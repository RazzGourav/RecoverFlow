#!/usr/bin/env python3
"""
Feature-parity cross-check: does what the BENCHMARK PIPELINE feeds the ML model
match what check_distribution.py (raw CSV -> real features) feeds it?

Method:
  1. Seed the same 100 held-out rows via run_final_benchmark.seed_cases()
     against a THROWAWAY SQLite in-memory DB (no Docker Postgres needed, no
     writes anywhere).
  2. For each seeded case, build_case_context(case, customer) exactly as
     run_decision_pipeline does, then build_features + predict + rank.
  3. Compare argmax distribution vs check_distribution.py's raw-CSV result.

Run with workers stopped; read-only w.r.t. any persistent store.
"""
import asyncio
import csv
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "apps" / "api"))
sys.path.insert(0, str(root_dir))

import pandas as pd

from ai.features.engineer import build_features, ACTION_TYPES, SEGMENTS
from ai.inference import predict
from domain.recovery.ranking import rank_candidate_actions
from domain.policies.pipeline import build_case_context


def argmax_dist(contexts):
    """contexts: list of raw case-context dicts -> top-action distribution."""
    predict.load_models()
    tops = []
    for ctx in contexts:
        df_single = pd.DataFrame([ctx])
        X_base = build_features(df_single)
        probs = {}
        for a in ACTION_TYPES:
            X_action = X_base.copy()
            for act in ACTION_TYPES:
                X_action[f"action_{act}"] = 1 if act == a else 0
            probs[a] = float(predict._intervention_model.predict_proba(X_action)[0, 1])
        ranked = rank_candidate_actions(ctx["amount_paise"], probs)
        tops.append(ranked[0].action_type)
    return pd.Series(tops).value_counts()


def main():
    # --- A. Raw CSV path (check_distribution.py equivalent) -------------------
    df_csv = pd.read_csv(root_dir / "data" / "processed" / "test.csv").head(100)
    csv_contexts = []
    for _, row in df_csv.iterrows():
        csv_contexts.append({
            "amount_paise": row["amount_paise"],
            "failure_type": row["failure_type"],
            "segment": row["segment"],
            "tenure_days": row["tenure_days"],
            "high_frequency_contact": False,
            "requires_human_review": False,
        })

    # --- B. Benchmark-seeded DB path ------------------------------------------
    async def seed_and_collect():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker, selectinload
        from sqlalchemy import select

        from db.models import RecoveryCase
        from scripts.run_final_benchmark import seed_cases

        from sqlalchemy.pool import StaticPool
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
        from db.models import Base
        import sqlalchemy.dialects.postgresql as pg_types
        from sqlalchemy.ext.compiler import compiles

        @compiles(pg_types.JSONB, "sqlite")
        def _jsonb_sqlite(type_, compiler, **kw):
            return "JSON"

        @compiles(pg_types.UUID, "sqlite")
        def _uuid_sqlite(type_, compiler, **kw):
            return "CHAR(32)"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with SessionLocal() as session:
            meta = await seed_cases(session)

            contexts = []
            stmt = (
                select(RecoveryCase)
                .options(selectinload(RecoveryCase.customer))
                .where(RecoveryCase.id.in_(meta["case_ids"]))
            )
            cases = (await session.execute(stmt)).scalars().all()

            # preserve original CSV order (seed order == CSV order)
            order = {cid: i for i, cid in enumerate(meta["case_ids"])}
            cases.sort(key=lambda c: order[c.id])

            from db.models import CustomerSegment  # noqa: F401 (informational print below)

            for case in cases:
                cust = case.customer
                ctx = build_case_context(case, customer=cust)
                contexts.append(ctx)

            # Also verify the stored DB segment distribution
            seg_counts = {}
            ml_seg_counts = {}
            tenure_real = 0
            for c in cases:
                db_seg = c.customer.segment.value if c.customer else None
                seg_counts[db_seg] = seg_counts.get(db_seg, 0) + 1
                mls = (c.customer.metadata_ or {}).get("ml_segment") if c.customer else None
                ml_seg_counts[mls] = ml_seg_counts.get(mls, 0) + 1
                if c.customer and c.customer.tenure_days and c.customer.tenure_days > 0:
                    tenure_real += 1

        return contexts, seg_counts, ml_seg_counts, tenure_real

    contexts_db, seg_counts, ml_seg_counts, tenure_real = asyncio.run(seed_and_collect())

    print("=" * 70)
    print("FEATURE PARITY CROSS-CHECK")
    print("=" * 70)
    print(f"\nCSV rows used: {len(csv_contexts)} | Seeded benchmark cases: {len(contexts_db)}")

    print("\n--- Segment values seen by the MODEL (benchmark path) ---")
    seg_seen = pd.Series([c["segment"] for c in contexts_db]).value_counts()
    print(seg_seen.to_string())
    bad_segs = [s for s in set(c["segment"] for c in contexts_db) if s not in SEGMENTS]
    print(f"Segments outside ML vocabulary: {bad_segs or 'NONE'}")

    print("\n--- tenure_days seen by the MODEL (benchmark path) ---")
    t = pd.Series([c["tenure_days"] for c in contexts_db])
    print(f"nonzero: {(t > 0).sum()}/{len(t)}, mean={t.mean():.1f}, min={t.min()}, max={t.max()}")

    print("\n--- Stored DB segment enum distribution (informational) ---")
    print(pd.Series(seg_counts).sort_values(ascending=False).to_string())
    print("\n--- Original CSV segment stashed in customer.metadata_ ---")
    print(pd.Series(ml_seg_counts).sort_values(ascending=False).to_string())

    print("\n--- Argmax distribution: RAW CSV (check_distribution.py) ---")
    dist_csv = argmax_dist(csv_contexts)
    print(dist_csv.to_string())

    print("\n--- Argmax distribution: BENCHMARK-SEEDED CASES (pipeline path) ---")
    dist_db = argmax_dist(contexts_db)
    print(dist_db.to_string())

    same = dist_csv.equals(dist_db)
    print(f"\nVERDICT: distributions identical? {same}")
    if not same:
        print("CSV :", dict(dist_csv))
        print("PIPE:", dict(dist_db))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
