You are working on RecoverFlow, an AI Revenue Recovery Control Plane, built for the
Razorpay /buildathon (Track 03). You are one of several agent sessions working on this
repo across a 16-day build. Treat every session as if a different engineer will pick up
your work tomorrow with zero context beyond the repo itself.

NON-NEGOTIABLE RULES:

1. PRODUCTION-GRADE CODE ONLY
   - Full type hints (Python: mypy-clean; TypeScript: strict mode, no `any`).
   - No TODOs left silently — if something is deferred, write it to docs/backlog.md
     with a reason and open a GitHub issue reference.
   - No hardcoded secrets, API keys, or credentials, ever. Use .env + .env.example.
   - No print()-based debugging left in committed code — use structured logging.
   - Every public function/class gets a docstring explaining WHY, not just WHAT.

2. REPRODUCIBILITY IS THE #1 PRIORITY
   - A reviewer must be able to run:
       git clone <repo> && cd recoverflow && cp .env.example .env && docker compose up --build
     and get a fully working system with ZERO manual steps beyond that.
   - Any new dependency must be pinned (exact version) in requirements.txt / package.json.
   - Any new environment variable must be added to .env.example with a comment.
   - Database schema changes must ship as a migration (Alembic), never a manual SQL step.
   - Synthetic data generation must be scripted and deterministic (fixed random seed).

3. TESTING IS MANDATORY, NOT OPTIONAL
   - Every phase must end with passing tests before you consider it done.
   - Unit tests for all business logic (policy engine, risk scoring, idempotency,
     feature calculation, action ranking).
   - Integration tests for every new API route and every new data flow.
   - Never mark a phase complete if `pytest` / `npm test` is red.
   - If you cannot make a test pass, STOP and report the blocker — do not comment out
     or skip the test to make CI green.

4. GIT DISCIPLINE
   - Small, atomic commits. Conventional commit format:
     feat(scope): ..., fix(scope): ..., test(scope): ..., docs(scope): ..., chore(scope): ...
   - Commit and push at every safe checkpoint (after each passing test suite run),
     not just once at the end of the day. Never leave more than ~30 minutes of
     uncommitted work.
   - Never force-push to main. Work on a feature branch per phase:
     `phase-0-foundation`, `phase-1-payment-events`, etc. Open a PR into main.
   - Before pushing, always run the full local check sequence (see "PRE-PUSH CHECK"
     below) so main never receives a commit that breaks the build.

5. NO FABRICATED CAPABILITIES
   - Never claim or implement a Razorpay API capability without it being explicitly
     confirmed against current Razorpay docs in this session. If unconfirmed, use the
     MockProvider and clearly label it as simulated in code comments, UI, and README.
   - The RazorpayProvider / MockProvider abstraction (see Phase 1) must be respected by
     every module that touches payments — never call a payment SDK directly from
     business logic.

6. SAFETY RAILS ARE CODE, NOT DECORATION
   - Every money-moving action must pass through the deterministic Policy Engine.
   - The LLM NEVER directly triggers an action. It only produces a structured,
     schema-validated recommendation that downstream deterministic code evaluates.
   - Every action, whether ALLOW/REVIEW/BLOCK, must write an audit_events row.
   - Idempotency keys are mandatory on every webhook-triggered write path.

7. DEMO-DAY SAFETY
   - Nothing you build today should be able to break a demo two weeks from now.
     Prefer boring, well-tested code over clever code.
   - Every phase must leave the system in a demoable state — `docker compose up`
     should always produce a running app, even if a feature is incomplete
     (feature-flag incomplete features off rather than leaving broken code live).

PRE-PUSH CHECK (run before every push, no exceptions):
  Backend:  ruff check . && mypy . && pytest -q
  Frontend: npm run lint && npm run typecheck && npm test -- --run
  Full stack: docker compose up --build -d && ./scripts/smoke_test.sh && docker compose down

If any of these fail, fix it before pushing. Do not push red.
before demo verify all the build with RecoverFlowPRD.md