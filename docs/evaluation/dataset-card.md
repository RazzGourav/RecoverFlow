# Dataset Card: Synthetic Recovery Dataset

## Overview
This dataset is **100% synthetically generated** and contains no real merchant or customer data. It is explicitly designed to simulate realistic payment failure scenarios, customer behaviors, and recovery outcomes for the purpose of testing, ML model training, and offline evaluation in RecoverFlow.

## Intended Use
- **Model Training (Phase 3)**: Train classification models to predict `actually_recovered` based on case features.
- **Offline Evaluation**: Serve as a static, deterministic benchmark to evaluate Policy Engine changes.
- **Local Development**: Populate local databases (`make seed-db`) with a realistic baseline state.

## Generation Process & Reproducibility
- **Seed**: `42` (Fixed deterministic seed)
- **Script**: `data/synthetic/generate.py`
- **Output**: Three splits (`train.csv`, `val.csv`, `test.csv`) stored in `data/processed/`.

Running the generation script with the same seed will produce bit-for-bit identical files.

## Dataset Fields
- `case_id`: Unique identifier for the recovery case.
- `segment`: Customer segment (`NEW`, `ESTABLISHED`, `HIGH_VALUE`).
- `tenure_days`: Number of days since the customer's first payment.
- `amount_paise`: Payment amount in smallest currency unit.
- `failure_type`: Reason for payment failure (`TEMPORARY`, `PAYMENT_METHOD`, `PERSISTENT`, `CUSTOMER_ACTION`, `UNKNOWN`).
- `action_taken`: The simulated action that was taken.
- `actually_recovered`: Ground-truth label (boolean) indicating if the payment was successfully recovered.

## Distributions & Edge Cases
The generator explicitly embeds structural variance and edge cases:
- **Unrecoverable Baseline**: Cases with `failure_type=PERSISTENT` have a forced 0% recovery rate.
- **Stale Webhooks**: Cases flagged as `is_stale=True` are forced to 100% recovery (payment arrived before intervention).
- **High-Value Escalation**: Amounts > 2,500,000 paise trigger `requires_human_review`.
- **Frequency Abuse**: `high_frequency_contact` flags cases that have exhausted policy limits.
- **Duplicates**: Roughly 3% of cases have a secondary duplicate row (`is_duplicate=True`) mirroring the exact `case_id` to test idempotency boundaries.

## Limitations
- **No Causal Accuracy**: The recovery probabilities are heavily simplified (e.g. `base_prob + modifier`). It does not represent actual market responsiveness.
- **Uniform Modifiers**: Human escalation boosts success uniformly by 25%, which is not realistic in a noisy, real-world cohort.
- **Action Selection is Random**: In reality, actions are chosen by a policy or model; in this dataset, they are assigned randomly, meaning the data contains inherent noise regarding optimal action paths.

**Important for Demo Day**: This dataset is completely synthetic. It guarantees structural validity (types, edge cases) but does not contain true causal insights from live merchant data.
