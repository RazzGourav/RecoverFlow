# data/

Datasets for training, evaluation, and synthetic demo generation.

This directory is intentionally empty in Phase 0.
Implementation begins in **Phase 2 (Recovery Data Engine)**.

## Sub-directories

| Directory | Purpose | Phase |
|---|---|---|
| `raw/` | Raw event logs (never modified after ingestion) | 2 |
| `synthetic/` | Deterministically generated synthetic cases (fixed seed) | 2 |
| `processed/` | Feature-engineered datasets ready for training | 2 |
| `schemas/` | JSON/YAML schemas validating all dataset files | 2 |

## Rules

- `raw/` and `synthetic/` files are **never** committed to Git if they exceed 10 MB.
- All synthetic generation scripts must accept `--seed INT` and produce identical output.
- Dataset schemas in `schemas/` are validated in CI.
