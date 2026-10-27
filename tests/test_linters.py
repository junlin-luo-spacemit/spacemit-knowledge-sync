from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint_terms = load_script("lint_terms")
lint_descriptions = load_script("lint_descriptions")


class TermLinterTests(unittest.TestCase):
    def test_ignores_forbidden_terms_in_inline_code_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            path = root / "sample.md"
            path.write_text(
                "Use `I2C` in code.\n"
                "[Reference](https://example.invalid/I2C)\n"
                "Use I2C for control.\n",
                encoding="utf-8",
            )

            config = {"exclude": []}
            glossary = [{"term": "I²C", "scope": "both", "forbidden_en": ["I2C"]}]
            results = lint_terms.scan(
                "fixture", {"path": str(root)}, glossary, config, None, None
            )

            self.assertEqual(1, len(results))
            self.assertIn("sample.md:3", results[0][1])

    def test_ignores_signal_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            path = root / "sample.md"
            path.write_text("Connect CAM_I2C0_SCL.\nUse I2C for control.\n", encoding="utf-8")

            config = {"exclude": []}
            glossary = [{"term": "I²C", "scope": "both", "forbidden_en": ["I2C"]}]
            results = lint_terms.scan(
                "fixture", {"path": str(root)}, glossary, config, None, None
            )

            self.assertEqual(1, len(results))
            self.assertIn("sample.md:2", results[0][1])


class DescriptionLinterTests(unittest.TestCase):
    def test_flags_noncanonical_variant(self) -> None:
        entity = {
            "attributes": [
                {
                    "key": "ai_compute",
                    "canonical_en": "2.0 TOPS",
                    "variants_en": ["2 TOPS", "2.0 TOPS"],
                }
            ]
        }

        self.assertEqual(
            ["WARN  ai_compute: '2.0 TOPS' expected, line uses ['2 TOPS']"],
            lint_descriptions.check_attributes("The K1 provides 2 TOPS.", entity, "en"),
        )

    def test_skips_canonical_value(self) -> None:
        entity = {
            "attributes": [
                {
                    "key": "ai_compute",
                    "canonical_en": "2.0 TOPS",
                    "variants_en": ["2 TOPS", "2.0 TOPS"],
                }
            ]
        }

        self.assertEqual(
            [], lint_descriptions.check_attributes("The K1 provides 2.0 TOPS.", entity, "en")
        )


if __name__ == "__main__":
    unittest.main()
