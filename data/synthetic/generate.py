#!/usr/bin/env python3
"""
RecoverFlow — Synthetic Data Generator

Why this file exists:
  Provides a reproducible, deterministic dataset of synthetic recovery cases.
  This data is used to train the ML engine (Phase 3), evaluate policies offline,
  and safely seed the local development/demo environment without exposing real PI.

Acceptance Criteria implemented here:
  - Fixed random seed (42) for byte-identical output across runs.
  - Realistic distributions of customer segments and failure types.
  - Edge cases explicitly injected:
      - Duplicate webhooks
      - Stale webhooks (already paid before we intervene)
      - High-amount cases needing human review
      - Suspicious high-frequency contacts
  - Permanently unrecoverable cases are strictly 0% recovery.
  - Splits into 60/20/20 Train/Val/Test with zero leakage.
  - Manifest JSON generated to track parameters.
"""

import csv
import json
import random
import uuid
from pathlib import Path

# The deterministic anchor.
SEED = 42

OUTPUT_DIR = Path(__file__).parent.parent / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configurations
TOTAL_CASES = 500

SEGMENTS = ["NEW", "ESTABLISHED", "HIGH_VALUE"]
SEGMENT_WEIGHTS = [0.4, 0.4, 0.2]

FAILURE_TYPES = [
    "TEMPORARY",
    "PAYMENT_METHOD",
    "PERSISTENT",
    "CUSTOMER_ACTION",
    "UNKNOWN",
]
FAILURE_WEIGHTS = [0.30, 0.40, 0.10, 0.15, 0.05]

ACTION_TYPES = [
    "RETRY",
    "PAYMENT_LINK",
    "INVOICE",
    "PAYMENT_METHOD_UPDATE",
    "REMINDER",
    "HUMAN_ESCALATION",
    "NO_ACTION",
]


def generate_case_features(idx: int):
    """Generate the base features for a case."""
    segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
    failure_type = random.choices(FAILURE_TYPES, weights=FAILURE_WEIGHTS)[0]

    # Tenure distributions based on segment
    if segment == "NEW":
        tenure_days = random.randint(1, 30)
    elif segment == "ESTABLISHED":
        tenure_days = random.randint(31, 365)
    else:
        tenure_days = random.randint(180, 1000)

    # Amount distributions based on segment
    if segment == "HIGH_VALUE":
        amount_paise = random.randint(50_000, 10_000_000)
    else:
        amount_paise = random.randint(1_000, 50_000)

    # Base case definition
    case = {
        "case_id": str(uuid.UUID(int=random.getrandbits(128), version=4)),
        "external_event_id": f"ev_{idx}_{random.randint(1000,9999)}",
        "segment": segment,
        "tenure_days": tenure_days,
        "amount_paise": amount_paise,
        "failure_type": failure_type,
        "action_taken": random.choice(ACTION_TYPES),
        "is_duplicate": False,
        "is_stale": False,
        "requires_human_review": False,
        "high_frequency_contact": False,
    }
    return case


def determine_recovery(case: dict) -> bool:
    """Ground truth logic simulator based on the designed schema."""
    if case["is_stale"]:
        return True  # Always "recovered" because it was already paid.
    if case["failure_type"] == "PERSISTENT":
        return False  # Unrecoverable.

    # Base probability by segment
    base_prob = 0.0
    if case["segment"] == "NEW":
        base_prob = 0.3
    elif case["segment"] == "ESTABLISHED":
        base_prob = 0.5
    elif case["segment"] == "HIGH_VALUE":
        base_prob = 0.7

    # Action modifiers based on failure type match
    action = case["action_taken"]
    ftype = case["failure_type"]

    if ftype == "TEMPORARY":
        base_prob += 0.2 if action == "RETRY" else 0.0
    elif ftype == "PAYMENT_METHOD":
        base_prob += 0.3 if action == "PAYMENT_METHOD_UPDATE" else -0.1
    elif ftype == "CUSTOMER_ACTION":
        base_prob += 0.2 if action == "PAYMENT_LINK" else -0.1

    if action == "HUMAN_ESCALATION" and case["segment"] == "HIGH_VALUE":
        base_prob += 0.25

    return random.random() < max(0.0, min(1.0, base_prob))


def main():
    # Enforce strict determinism
    random.seed(SEED)

    cases = []
    
    # 1. Generate base cases
    for i in range(TOTAL_CASES):
        case = generate_case_features(i)
        
        # Inject Edge Cases (~15 per 500 records)
        
        # High amount > 25,000 INR
        if i % 30 == 0:
            case["amount_paise"] = random.randint(2_500_000, 5_000_000)
            case["requires_human_review"] = True
            case["segment"] = "HIGH_VALUE"
        
        # Stale webhook
        elif i % 31 == 1:
            case["is_stale"] = True
            case["action_taken"] = "NO_ACTION"
            
        # Suspicious frequency
        elif i % 32 == 2:
            case["high_frequency_contact"] = True
            case["action_taken"] = "HUMAN_ESCALATION"

        # Determine ground truth recovery based on features + injected flags
        case["actually_recovered"] = determine_recovery(case)
        cases.append(case)
        
        # Duplicate pair injection
        if i % 33 == 3:
            duplicate = case.copy()
            # duplicate has same case_id, external_event_id, but flagged
            duplicate["is_duplicate"] = True
            # For data hygiene, usually duplicates don't yield independent actions, 
            # but we include it in the raw dataset to teach the ML/Risk layer.
            cases.append(duplicate)

    # 2. Split logic (No leakage: group by case_id)
    # We must ensure all duplicates of a case_id stay in the same split.
    unique_cases = {}
    for c in cases:
        if c["case_id"] not in unique_cases:
            unique_cases[c["case_id"]] = []
        unique_cases[c["case_id"]].append(c)
        
    case_ids = list(unique_cases.keys())
    random.shuffle(case_ids)
    
    train_bound = int(0.6 * len(case_ids))
    val_bound = int(0.8 * len(case_ids))
    
    splits = {
        "train": [c for cid in case_ids[:train_bound] for c in unique_cases[cid]],
        "val": [c for cid in case_ids[train_bound:val_bound] for c in unique_cases[cid]],
        "test": [c for cid in case_ids[val_bound:] for c in unique_cases[cid]],
    }
    
    # 3. Write to CSV
    metrics = {}
    fieldnames = list(cases[0].keys())
    
    for split_name, split_data in splits.items():
        filepath = OUTPUT_DIR / f"{split_name}.csv"
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(split_data)
        
        metrics[split_name] = len(split_data)

    # 4. Write manifest
    manifest = {
        "seed": SEED,
        "total_generated": len(cases),
        "splits": metrics,
        "parameters": {
            "segments": SEGMENTS,
            "failure_types": FAILURE_TYPES,
        }
    }
    
    with open(OUTPUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(cases)} synthetic cases deterministically (SEED={SEED}).")
    for k, v in metrics.items():
        print(f"   {k}: {v} rows")
    print(f"Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
