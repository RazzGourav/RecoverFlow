"""
Benchmark Reproducibility Test

Why this exists:
  Ensures that the offline ML-inference component of the benchmark (reading
  the held-out test split, running feature engineering, scoring all actions
  via the trained intervention model) produces byte-identical results across
  two independent runs.  This is the same determinism guarantee that
  test_synthetic_data.test_reproducibility provides for the data generation
  step.

  The full benchmark (scripts/run_final_benchmark.py) requires a running
  PostgreSQL instance and exercises the real DB-backed decision pipeline.
  This test exercises the ML-only path that determines strategy-level
  expected-recovery numbers, which is the core of what makes the benchmark
  report reproducible from a fresh clone.
"""

from pathlib import Path

import pandas as pd
import pytest

from ai.features.engineer import ACTION_TYPES, build_features
from ai.inference import predict


def _find_project_root() -> Path:
    """Walk up from this file's location until we find pytest.ini (project root marker)."""
    candidate = Path(__file__).resolve().parent
    for _ in range(10):
        if (candidate / "pytest.ini").exists():
            return candidate
        candidate = candidate.parent
    raise RuntimeError("Could not find project root (no pytest.ini found)")


PROJECT_ROOT = _find_project_root()
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TEST_CSV = PROCESSED_DIR / "test.csv"
BENCHMARK_N = 100


def _run_benchmark_inference(test_df: pd.DataFrame) -> dict:
    """Run ML inference on the test split and return deterministic results.

    This mirrors the exact computation path used in simulation_core.py's
    RECOVERFLOW_OPTIMAL strategy and in scripts/check_distribution.py.
    """
    predict.load_models()

    results: list[dict] = []
    for _, row in test_df.iterrows():
        case_data = {
            "amount_paise": int(row["amount_paise"]),
            "failure_type": str(row["failure_type"]),
            "segment": str(row["segment"]),
            "tenure_days": int(row["tenure_days"]),
        }

        df_single = pd.DataFrame([case_data])
        X_base = build_features(df_single)

        # Recovery model
        recov_prob = float(predict._recovery_model.predict_proba(X_base)[0, 1])

        # Intervention model — score all actions
        action_probs: dict[str, float] = {}
        for action in ACTION_TYPES:
            X_action = X_base.copy()
            for a in ACTION_TYPES:
                X_action[f"action_{a}"] = 1 if a == action else 0
            prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
            action_probs[action] = prob

        best_action = max(action_probs, key=action_probs.get)  # type: ignore[arg-type]
        best_prob = action_probs[best_action]

        results.append({
            "segment": case_data["segment"],
            "failure_type": case_data["failure_type"],
            "amount_paise": case_data["amount_paise"],
            "recoverability": round(recov_prob, 8),
            "best_action": best_action,
            "best_prob": round(best_prob, 8),
            "expected_recovery_paise": round(best_prob * case_data["amount_paise"], 2),
        })

    total_expected_recovery = sum(r["expected_recovery_paise"] for r in results)
    action_dist = {}
    for r in results:
        action_dist[r["best_action"]] = action_dist.get(r["best_action"], 0) + 1

    return {
        "n_cases": len(results),
        "total_expected_recovery": round(total_expected_recovery, 2),
        "action_distribution": action_dist,
        "per_case": results,
    }


@pytest.fixture(scope="module")
def test_df() -> pd.DataFrame:
    """Load the fixed test split exactly as the benchmark does."""
    assert TEST_CSV.exists(), (
        f"Test CSV not found at {TEST_CSV}. "
        "Run `python -m data.synthetic.generate` to create it."
    )
    df = pd.read_csv(TEST_CSV)
    return df.head(BENCHMARK_N)


def test_benchmark_produces_results(test_df: pd.DataFrame) -> None:
    """Smoke test: benchmark inference runs and returns plausible results."""
    result = _run_benchmark_inference(test_df)

    assert result["n_cases"] == BENCHMARK_N
    assert result["total_expected_recovery"] > 0, (
        "Expected recovery should be positive for at least some cases"
    )
    assert len(result["per_case"]) == BENCHMARK_N
    assert len(result["action_distribution"]) >= 1, (
        "At least one action type should be selected"
    )


def test_benchmark_reproducibility(test_df: pd.DataFrame) -> None:
    """Two independent runs produce identical numbers.

    This is the core determinism guarantee: same data + same model weights
    + same feature engineering = same numbers every time.
    """
    run1 = _run_benchmark_inference(test_df)
    run2 = _run_benchmark_inference(test_df)

    # Top-level aggregates must be exactly equal
    assert run1["n_cases"] == run2["n_cases"]
    assert run1["total_expected_recovery"] == run2["total_expected_recovery"], (
        f"Total expected recovery differs between runs: "
        f"{run1['total_expected_recovery']} vs {run2['total_expected_recovery']}"
    )
    assert run1["action_distribution"] == run2["action_distribution"], (
        f"Action distribution differs: "
        f"{run1['action_distribution']} vs {run2['action_distribution']}"
    )

    # Per-case results must be identical
    for i, (r1, r2) in enumerate(zip(run1["per_case"], run2["per_case"])):
        assert r1["best_action"] == r2["best_action"], (
            f"Case {i}: best_action differs: {r1['best_action']} vs {r2['best_action']}"
        )
        assert r1["best_prob"] == r2["best_prob"], (
            f"Case {i}: best_prob differs: {r1['best_prob']} vs {r2['best_prob']}"
        )
        assert r1["recoverability"] == r2["recoverability"], (
            f"Case {i}: recoverability differs: "
            f"{r1['recoverability']} vs {r2['recoverability']}"
        )


def test_no_hardcoded_probabilities_in_benchmark_path() -> None:
    """Grep-equivalent test: confirm no `0.75 if` or `else 0.25` patterns
    exist in the benchmark script, seed script, or simulation core.

    This test reads the actual source files and asserts the fabricated-probability
    pattern is gone. It exists so the problem can never silently reappear.
    """
    root = PROJECT_ROOT
    files_to_check = [
        root / "scripts" / "run_final_benchmark.py",
        root / "scripts" / "seed_db.py",
        root / "ai" / "evaluation" / "simulation_core.py",
        root / "ai" / "inference" / "predict.py",
    ]

    for filepath in files_to_check:
        assert filepath.exists(), f"Expected file not found: {filepath}"
        content = filepath.read_text(encoding="utf-8")

        # The specific fabricated pattern from the audit finding
        assert "0.75 if actually_recovered else 0.25" not in content, (
            f"Hardcoded fabricated probability found in {filepath.name}! "
            f"This is the pattern identified in the system integrity audit "
            f"as circular (using ground-truth labels to fake predictions)."
        )

        # Also check for the derived-baseline pattern
        assert "naive_recovery = int(res_optimal" not in content, (
            f"Derived naive baseline found in {filepath.name}! "
            f"Baselines must be computed independently, not derived from "
            f"the optimal result."
        )
