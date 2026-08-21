"""
RecoverFlow — Tests for Synthetic Data Generation

Ensures that our mock data generator is fully deterministic, leak-free,
and produces structurally sound distributions.
"""

import csv
import filecmp
from pathlib import Path
from unittest.mock import patch

from data.synthetic.generate import main


def test_reproducibility(tmp_path: Path) -> None:
    """
    Regenerating the dataset with the same seed produces byte-identical output.
    """
    # Run 1
    dir1 = tmp_path / "run1"
    dir1.mkdir()
    with patch("data.synthetic.generate.OUTPUT_DIR", dir1):
        main()

    # Run 2
    dir2 = tmp_path / "run2"
    dir2.mkdir()
    with patch("data.synthetic.generate.OUTPUT_DIR", dir2):
        main()

    # Compare files
    files1 = {f.name: f for f in dir1.iterdir()}
    files2 = {f.name: f for f in dir2.iterdir()}
    
    assert set(files1.keys()) == set(files2.keys())
    assert "train.csv" in files1
    
    for filename in files1:
        assert filecmp.cmp(files1[filename], files2[filename], shallow=False), f"{filename} is not byte-identical!"


def test_split_leakage(tmp_path: Path) -> None:
    """
    No case_id appears in more than one split (no leakage).
    """
    with patch("data.synthetic.generate.OUTPUT_DIR", tmp_path):
        main()

    def get_case_ids(filename: str) -> set[str]:
        ids = set()
        with open(tmp_path / filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.add(row["case_id"])
        return ids

    train_ids = get_case_ids("train.csv")
    val_ids = get_case_ids("val.csv")
    test_ids = get_case_ids("test.csv")

    assert train_ids.isdisjoint(val_ids), "Leakage between train and val!"
    assert train_ids.isdisjoint(test_ids), "Leakage between train and test!"
    assert val_ids.isdisjoint(test_ids), "Leakage between val and test!"


def test_distribution_sanity(tmp_path: Path) -> None:
    """
    Check basic constraints: e.g., PERSISTENT cases never recover.
    """
    with patch("data.synthetic.generate.OUTPUT_DIR", tmp_path):
        main()
        
    all_rows = []
    for split in ["train.csv", "val.csv", "test.csv"]:
        with open(tmp_path / split, "r", encoding="utf-8") as f:
            all_rows.extend(list(csv.DictReader(f)))
            
    assert len(all_rows) > 0
    
    persistent_cases = [r for r in all_rows if r["failure_type"] == "PERSISTENT"]
    assert len(persistent_cases) > 0, "No PERSISTENT cases generated!"
    
    for case in persistent_cases:
        if case["is_stale"] == "True":
            continue
        assert case["actually_recovered"] == "False", f"PERSISTENT case recovered?! Case: {case}"
        
    stale_cases = [r for r in all_rows if r["is_stale"] == "True"]
    assert len(stale_cases) > 0, "No stale cases generated!"
    for case in stale_cases:
        assert case["actually_recovered"] == "True", "Stale case did not 'recover'"
