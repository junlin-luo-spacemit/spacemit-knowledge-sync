from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_CHIP = ROOT.parent / "docs-chip"
CONSUMER_AGENT = DOCS_CHIP / ".github" / "doc-review-agent"
V100_ZH_DOC = DOCS_CHIP / "zh" / "vital_stone" / "v100" / "v100_docs" / "root_overview.md"

CONSUMER_AVAILABLE = (
    CONSUMER_AGENT.is_dir()
    and (CONSUMER_AGENT / "knowledge_sync.py").exists()
    and V100_ZH_DOC.exists()
)


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


def load_consumer_knowledge_sync():
    spec = importlib.util.spec_from_file_location(
        "knowledge_sync", CONSUMER_AGENT / "knowledge_sync.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SYNC_REPO = Path(__file__).resolve().parents[1]

FIXTURE_ZH = (
    "V100 集成 46 个 RISC-V CPU 核，主频最高可达 2.4GHz。\n"
    "外围接口：4×I3C、12×I2C、12×SMBUS。\n"
)
FIXTURE_REL = "zh/vital_stone/v100/v100_docs/root_overview.md"


@unittest.skipUnless(CONSUMER_AVAILABLE, "docs-chip consumer agent not available")
class ConsumerContractTests(unittest.TestCase):
    """Verify canonical YAML is consumable by the docs-chip review agent.

    Copies the canonical glossary and entities into a temporary agent layout
    together with the consumer's own knowledge_sync.py, then asserts the agent
    parses them without error and reports known findings. This catches schema
    drift between this repository and the consumer parser regardless of whether
    the consumer repository has merged the latest sync.
    """

    @classmethod
    def setUpClass(cls):
        import shutil

        cls._tmp = tempfile.TemporaryDirectory()
        agent = Path(cls._tmp.name)
        shutil.copy2(CONSUMER_AGENT / "knowledge_sync.py", agent / "knowledge_sync.py")
        shutil.copy2(SYNC_REPO / "glossary.yaml", agent / "glossary.yaml")
        shutil.copytree(SYNC_REPO / "entities", agent / "entities")

        spec = importlib.util.spec_from_file_location(
            "knowledge_sync_contract", agent / "knowledge_sync.py"
        )
        assert spec and spec.loader
        cls.ks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ks)
        cls.lines = FIXTURE_ZH.splitlines()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_agent_loads_canonical_glossary(self) -> None:
        glossary = self.ks.load_glossary()
        self.assertGreater(len(glossary), 0, "consumer parser returned no glossary entries")
        terms = {entry.get("term") for entry in glossary}
        self.assertIn("SMBus", terms, "canonical glossary SMBus rule not visible to consumer")

    def test_agent_loads_canonical_entities(self) -> None:
        entities = self.ks.load_entities()
        names = {entity.get("entity") for entity in entities}
        self.assertIn("V100", names)
        self.assertIn("V100 Products", names)

    def test_agent_flags_terminology_drift(self) -> None:
        messages = [m for _, _, m in self.ks.check_terminology(self.lines, FIXTURE_REL)]
        self.assertTrue(any("SMBUS" in m for m in messages), messages)
        self.assertTrue(any("I2C" in m for m in messages), messages)

    def test_agent_flags_entity_drift(self) -> None:
        messages = [m for _, _, m in self.ks.check_descriptions(self.lines, FIXTURE_REL)]
        self.assertTrue(
            any("max_frequency" in m for m in messages),
            f"expected max_frequency finding, got {messages}",
        )


if __name__ == "__main__":
    unittest.main()
