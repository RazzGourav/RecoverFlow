# Final Pre-Demo Audit Report

This report serves as an honest, evidence-based inventory of the RecoverFlow system stack, cross-referencing UI, API, and webhook layers against the PRD requirements.

---

## Part A — Full Frontend Feature Inventory

### 1. Screen / Route Inventory

| Screen / Route | Purpose (per PRD) | Status | Evidence |
|---|---|---|---|
| `/` (Control Tower) | High-level metrics, live case feed, risk alerts | WORKING | `app/page.tsx` renders metrics and live case list |
| `/audit` (Audit Explorer) | Immutable log of all system decisions | WORKING | Functional table populated from `api/audit/` |
| `/cases` (Recovery Cases) | Filterable list view of all cases | WORKING | `app/cases/page.tsx` -> `CasesTable.tsx` |
| `/cases/[id]` (Case Intelligence) | Deep dive into a single case lifecycle | WORKING | `app/cases/[id]/ClientCase.tsx` renders full pipeline |
| `/cases/[id]/replay` | Interactive debugger for events | WORKING | `app/cases/[id]/replay/page.tsx` |
| `/failures` (Failure Center) | Root cause analysis & timeline | WORKING | `app/failures/page.tsx` |
| `/leak-graph` (Revenue Leak) | Visual funnel of where drop-offs occur | WORKING | `LeakGraph.tsx` rendering active Recharts data |
| `/policies` (Policy Studio) | Define merchant guardrails | WORKING | `app/policies/page.tsx` |
| `/simulation` (Simulation Lab) | Compare AI strategies on historical data | WORKING | `app/simulation/page.tsx` |

### 2. Interactive Elements Checklist

| Screen | Element | Expected Action | API Called | Result | Verdict |
|---|---|---|---|---|---|
| **Control Tower** | View Case Link | Navigate to case details | N/A (Client route) | Navigates to `/cases/[id]` | WORKING (real) |
| **Cases** | Client-side Tabs | Filter cases (All, High Risk, etc) | None (In-memory filter) | Table re-renders with matches | PARTIALLY IMPLEMENTED (State mismatch, see Note A) |
| **Case Intel** | Approve Button | Approves AWAITING_HUMAN case | `POST /api/cases/{id}/approve` | Returns 200, updates UI state | WORKING (real) |
| **Case Intel** | Reject Button | Rejects AWAITING_HUMAN case | `POST /api/cases/{id}/reject` | Returns 200, updates UI state | WORKING (real) |
| **Failure Ctr** | Simulate 2AM Incident | Fires a test failure incident | `POST /api/audit/trigger-incident`| Returns 200, reloads list | WORKING (real) |
| **Leak Graph** | "View Impacted Cases" | Navigate to Cases filtered by block | N/A (Client route) | Navigates to `/cases?filter=blocked` | BROKEN (See Note B) |
| **Simulation** | Run Simulation | Executes batch simulation | `POST /api/simulation/run` | Returns results, updates chart | WORKING (real) |

**Note A (Human Review Filter Bug):** The `HUMAN_REVIEW` filter button on the Cases Table expects `c.status === "HUMAN_REVIEW"`. However, the backend maps this to `CaseStatus.AWAITING_APPROVAL` and `Action.authorization_status = AWAITING_HUMAN`. Clicking the Human Review button yields 0 results even when cases exist.
**Note B (Leak Graph Link Mismatch):** The "View Impacted Cases" button in the Leak Graph links to `/cases?filter=blocked`. However, the `CasesTable` ignores query parameters completely (`useState("ALL")`), resulting in the user seeing the default unfiltered "All Cases" view.

### 3. PRD UI/UX Requirements Mapping (Section 16)

*   **Control Tower**: Fully in UI.
*   **Audit Explorer**: Fully in UI.
*   **Case Intelligence**: Fully in UI.
*   **Policy Studio**: Fully in UI.
*   **Failure Center**: Fully in UI.
*   **Event Replay Lab**: Fully in UI.
*   **Revenue Leak Graph**: Fully in UI.
*   **Human Approval Workflow**: Partially in UI (Approval/Reject works on Case detail, but list filtering is broken).

---

## Part B — Where is Razorpay in the Frontend?

**Verdict:** The system explicitly and visibly labels Razorpay vs Mock integration.

**Evidence:**
*   **"Where do I click to show a judge the Razorpay integration?"** -> Navigate to **any executed case** in the Case Intelligence screen. In the "Execution & Reconciliation" section, there is a dedicated `ProviderBadge`. If `PAYMENT_PROVIDER=razorpay` in `.env`, a blue live badge reads `● Payment Provider: Razorpay (Test Mode)`. Furthermore, the **Provider Reference** section displays the actual Razorpay payment link URL as a clickable outbound link.
*   *Code Evidence:* `apps/web/app/components/DataSourceBadge.tsx` and `ClientCase.tsx`.

---

## Part C — Real-Time Behavior Audit

1.  **Control Tower (Feed & Metrics):** **Polling (5 seconds)**. `app/page.tsx` uses a `setInterval` that fires `fetchData()` every 5 seconds.
2.  **Failure Center:** **Manual Refresh**. There is no auto-polling, except for an artificial 2-second reload after clicking "Simulate 2AM Incident".
3.  **Revenue Leak Graph:** **Snapshot-on-load**. Data is fetched once upon mount and does not live-update while viewing.

**Measured Latency Test:**
A Python script (`measure_latency.py`) fired a webhook to `/api/webhooks/razorpay` and continuously polled `/api/metrics` every 50ms to time the exact moment `total_cases` incremented.
*   **Measured End-to-End Latency:** The system processes the webhook, evaluates the policy, and commits the state in **~0.150 - 0.200 seconds**.
*   **UI Visibility Latency:** Because the Control Tower polls every 5 seconds, the absolute maximum time a judge will wait to see a fired webhook appear on the screen is **5.0 seconds** (average 2.5 seconds).

---

## Part D — Human Approval Workflow: Full Audit

**Status: Functional with one UI filtering gap.**

*   **Findability (BROKEN):** As identified in Part A, the "Human Review" filter in the Cases table is disconnected from the backend state. A judge cannot easily "filter" to find AWAITING_HUMAN cases without scrolling manually.
*   **Approval Functionality (WORKING):** Clicking "Approve" successfully sends a `POST` to `/cases/{id}/approve`. The backend transitions `authorization_status` from `AWAITING_HUMAN` to `APPROVED`, generating a strict `audit_events` trail (verified via integration tests `test_human_approval.py`). The action then securely resumes the standard execution pipeline.
*   **Rejection Functionality (WORKING):** Clicking "Reject" transitions the state to `BLOCKED` and the case to `SUPPRESSED`.

---

## Part E — Critical/High-Risk Transaction Simulation Trigger

**Status: Verified & Working.**

*   **Trigger:** We built/verified `scripts/trigger_critical_case.py`. It deliberately injects a failed payment webhook for **₹30,000** (tripping the high-value human approval threshold).
*   **UI Alert:** When fired, the case successfully enters the DB, and the Control Tower immediately renders a red **"Risk Firewall Engaged"** banner at the top of the screen (`app/page.tsx` line 115).
*   **Decision Trail:** Opening the case in Case Intelligence explicitly highlights the `AWAITING_HUMAN` status, with the Risk assessment showing exactly why it was held back.

---

## Part F — "How Does It Recover Money" End-to-End Visual Trace

**Verdict:** The visual trail is **COMPLETE**. It does not break down at any point.

1.  Webhook fired -> Case appears in Control Tower.
2.  Case opened -> AI Recoverability score visible.
3.  Candidate Actions -> Ranked list of strategies visible.
4.  Policy Engine -> Risk level and guardrails visible.
5.  Execution -> "Provider Reference" block displays the live Mock/Razorpay link ID.
6.  Reconciliation -> **"Reconciliation: MATCHED"** block explicitly states "₹X,XXX verified recovered."
7.  Global State -> Navigating back to the Control Tower reveals the "Recovered this Period" metric visibly higher.

---

## Part G — Backend Check

*   API Routes: All REST endpoints (metrics, cases, webhooks, simulation) are online and responding with correct JSON shapes.
*   Tests: The backend unit/integration tests correctly enforce constraints (e.g. `test_human_approval.py`, `test_budget_safety.py`).
*   *(Note: Running `pytest` locally on the Windows host fails due to `getaddrinfo` resolving `postgres:5432` since tests are hardcoded to the docker network hostname, but execution inside the container works properly).*

---

## Final Prioritized Punch List (Demo Risk)

1.  **[High] Case Table Filter Bug:** The "Human Review" tab in the cases table shows 0 results because of a status string mismatch (`HUMAN_REVIEW` vs `AWAITING_APPROVAL`). If a judge asks you to "show me the cases waiting for my approval," you will have to manually hunt for them instead of clicking the tab.
2.  **[High] Leak Graph Deep Link Bug:** Clicking "View Impacted Cases" in the Leak Graph navigates to `/cases?filter=blocked`, but the Cases table doesn't read query parameters. It just loads all cases.
3.  **[Medium] Failure Center Auto-Refresh:** The Failure Center doesn't poll. If you demo an external system crashing, you must manually refresh the page to see the error appear.
