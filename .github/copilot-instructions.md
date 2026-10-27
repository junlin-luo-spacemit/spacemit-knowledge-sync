# SpacemiT Documentation Agent Instructions

You are assisting with SpacemiT chip documentation. Use the canonical terminology and product descriptions defined in this repository's YAML files.

## Terminology Rules

Apply these terminology rules from [`glossary.yaml`](../glossary.yaml):

### Hardware & Architecture

- **boot sequence** (启动序列) — not 启动流程, 引导序列, 开机顺序
- **register map** (寄存器映射) — not 寄存器图, register table map
- **memory map** (内存映射) — not 存储器映射, 内存分布图
- **thermal dissipation** (散热方案) — not 散热设计, 热解决方案, heat dissipation solution
- **power rail** (电源轨) — not 电源轨线, 供电轨
- **evaluation board** (评估板) — prefer EVB after first mention; not evaluation card, eval board
- **schematic** (原理图) — not 原理电路图, 电路原理图, principle diagram
- **layout guideline** (布局布线规范) — not layout rule, wiring guideline, 布局规则
- **signal integrity** (信号完整性) — not 信号完整度
- **interrupt controller** (中断控制器) — not 中断控制单元

### Interfaces & Protocols

- **I²C** (I²C) — use superscript form; not I2C, IIC, IIC bus
- **product brief** (产品简介) — not product introduction, brief introduction, 产品概述简介

### Units & Formatting

- **Temperature range**: Use degree sign ° (U+00B0), not ˚ (U+02DA) or ℃ (U+2103)
  - Correct: `-40°C ～ 85°C`
  - Wrong: `-40˚C～85˚C`, `-40℃～85℃`

- **Package dimensions**: Use spaces around `x`
  - Correct: `7 mm x 7 mm`
  - Wrong: `7mmx7mm`, `7mm x 7mm`

- **AI compute**: Use TOPS as the unit
  - Correct: `2.0 TOPS`, `60 TOPS`
  - Wrong: `2 TOPS` (missing decimal), `AI power`, `AI compute`

- **Large model size**: Use B notation, not 亿/billion words
  - Correct: `30B`
  - Wrong: `300亿`, `30 billion`

## Product Entities

Use these canonical descriptions from [`entities/*.yaml`](../entities/):

### K1 (Key Stone K1)

**Canonical description (EN)**: SpacemiT Key Stone K1 is a high-performance and ultra-low-power SoC that integrates 8 RISC-V CPU cores with SpacemiT Daoyi AI computing power.

**Canonical description (ZH)**: K1 系列是 8 核 64 位 RISC-V AI CPU，采用同构融合计算技术，集成 8 个高性能 X60 计算核，提供 50KDMIPS 通用算力与 2 TOPS AI 算力。

**Key attributes**:
- CPU cores: `8-core` / `8 核` (not 八核, eight-core, octa-core)
- Core name: `X60` (not X60™)
- L2 cache: `shared 1 MB L2 across 8 cores` / `八核共享 1 MB L2`
- AI compute: `2.0 TOPS` (not 2 TOPS)

### K3 (Key Stone K3)

**Canonical description (EN)**: K3 is a high-performance RISC-V AI CPU capable of running 30B large models.

**Canonical description (ZH)**: K3 是运行 30B 大模型的高性能 RISC-V AI CPU。

**Key attributes**:
- CPU core name: `X100` (not X100™)
- AI core name: `A100` (not A100™)
- AI compute: `60 TOPS` (not 60TOPS)
- Model size: `30B` (not 300亿, 30 billion)

### P1 (Power Stone P1)

**Canonical description (EN)**: P1 is a high-performance multi-channel power management chip (PMIC) designed to provide customized power solutions for complex computing systems.

**Canonical description (ZH)**: P1 是一款高性能多通道电源管理芯片（PMIC），旨在为复杂计算系统提供定制化电源解决方案。

**Key attributes**:
- LDO count: `12 LDO` (not 12 LDOs, twelve LDO, 12 个 LDO)
- Buck converters: `6 buck converters` / `6 个降压转换器` (not 6 buck, 6 COT buck)
- Package: `QFN-60 (7 mm x 7 mm)` / `QFN-60（7 mm x 7 mm）` (not 7mmx7mm)

### P1S (Power Stone P1S)

Similar PMIC to P1; refer to [`entities/p1s.yaml`](../entities/p1s.yaml) for specific attributes.

### Muse Pi

Refer to [`entities/muse_pi.yaml`](../entities/muse_pi.yaml) for board-specific attributes.

## Documentation Tasks

When editing or reviewing SpacemiT documentation:

1. **Apply terminology rules consistently** — use the preferred forms listed above
2. **Match canonical product descriptions** — paraphrase the canonical descriptions rather than inventing new ones
3. **Verify technical attributes** — ensure specs match the entity YAML files (core counts, frequencies, package dimensions)
4. **Format units correctly** — follow the unit conventions (degree signs, spacing, TOPS notation)
5. **Maintain CN/EN consistency** — Chinese and English files should be translation pairs, not divergent content

## Source of Truth

For technical specifications, always refer to:
- **K1**: `en/key_stone/k1/k1_docs/k1_ds.md` (EN) / `zh/key_stone/k1/k1_docs/k1_ds.md` (ZH)
- **K3**: `en/key_stone/k3/k3_docs/root_overview.md` (EN) / `zh/key_stone/k3/k3_docs/root_overview.md` (ZH)
- **P1**: `en/power_stone/p1/p1_docs/root_overview.md` (EN) / `zh/power_stone/p1/p1_docs/root_overview.md` (ZH)

When you're unsure about a product fact, say so rather than guessing. Check the entity YAML files or ask the user to verify against the source documents.

## Validation

After editing documentation:
- Run `python scripts/lint_terms.py` to check terminology consistency
- Run `python scripts/lint_descriptions.py` to check product description consistency
- Review reported file:line findings and fix any flagged issues
