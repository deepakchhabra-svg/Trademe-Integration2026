## A) Executive Verdict

**NEEDS FIXES**

- **Playwright smoke currently fails in a clean environment**: the link-crawler hits `/pipeline/:id` which 500s due to missing Power auth, and it also finds a 404 doc link (local run evidence from code + runtime behavior). See `services/web/tests/links.spec.ts:L8-L101` and `services/web/src/app/pipeline/[supplierId]/page.tsx:L21-L22`.
- **A production endpoint explicitly bypasses a core guardrail**: `/validate/internal-products/{id}` runs LaunchLock with `test_mode=True`, which bypasses the trust gate. See `services/api/main.py:L2353-L2371` and `retail_os/core/validator.py:L26-L103`.
- **RBAC is easy to misconfigure into “header-based admin”**: tests set `RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES=true`, which would allow privilege escalation via a plain role header if accidentally enabled in production. See `.env.example:L36-L47`, `services/api/main.py:L205-L225`, `tests/test_schema_and_media.py:L105-L224`.
- **Operator UX has confusing “role switching” that doesn’t actually grant access** (unless insecure header roles are enabled or a token is configured), which risks operator mistakes and “it worked in CI” false confidence. See `services/web/src/app/_components/RoleSwitcher.tsx:L6-L35` and `services/api/main.py:L205-L225`.
- **Repo history includes unsafe committed artifacts** (SQLite DBs + Playwright reports/traces) in recent commits; even if later deleted, merging unsquashed can permanently embed them in main history. Evidence: `git show fd95e13` / `git show 9440a6f` included `dev_db.sqlite*` and `services/web/test-results/*`.

---

## B) Change Map (What changed)

**Scope note**: the branch contains more than the “Jan 2” snippet; below is a focused change map of the most relevant recent commits impacting UI, ops safety, tests, and CI.

| Commit | Area | Risk level | Notes |
|---|---|---:|---|
| `8b327a8` | Backend + UI | **Medium** | Adds bulk withdraw endpoint and UI; also changes media path handling and enrichment “Source” injection. Needs guardrails (confirmation + duplicate prevention) for mass-withdraw. |
| `7c0e739` | UI | Low | Removes unused state from Workbench (cleanup). |
| `4220b76` | UI / Operator IA | **Medium** | Refactors to reduce duplicate controls, pushes operators toward Pipeline; ensure legacy pages don’t remain “half-functional”. |
| `d4aab83` | Backend correctness | **Medium** | Category mapping changes + taxonomy JSON import; impacts publish gates and category selection. |
| `f263454` | Backend publish config + UI | **High** | Adds UI-managed shipping/footer; touches listing payload generation and worker config. Publishing/fees impacted. |
| `8651f3b` | Backend security + repo hygiene | **Medium** | Purges “unsafe artifacts” and removes hardcoded shipping/footer; introduces diagnostics scripts. Verify no secrets/log artifacts are committed. |
| `4629a44` | Trade Me ops | **High** | “Production readiness / transparency” touches TradeMe API + worker + UI health; mistakes here impact money and listings. |
| `fd95e13` | CI + Playwright | **High** | Adds Playwright webServer stack boot and touches worker; commit also included DB + Playwright report artifacts in history (bad). |
| `271ccf9` | CI | **High** | Changes CI behavior for “real mode seeded data” (but current CI does not run a seeder). Validate external-call prevention. |
| `d3f58a6` | E2E harness | **Medium** | Introduces “test mode” concepts; verify they cannot leak to production behavior. |
| `0c96f31` | Tests | **Medium** | Expands UI route/link coverage and workflow tests; currently these can fail without auth seeding/tokens. |
| `c133000` | Tooling | Low | Lint fixes + ignores; commit history includes Playwright artifacts (should never be committed). |
| `9440a6f` | Tooling | Low | Playwright report data committed in history (should never be committed). |

---

## C) Security Audit (Highest priority)

### Auth bypass / role defaults

- **No `NEXT_PUBLIC_DEFAULT_ROLE` found in this branch** (repo-wide search). If it exists in another branch/PR, re-run this audit there; it is a common “tests pass by bypass” smell.
- **RBAC design**: server trusts a configured token (`X-RetailOS-Token`) to assign a role; plain `X-RetailOS-Role` is intentionally downgraded unless `RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES=true`. See `services/api/main.py:L198-L225`.

### /media endpoint traversal / unintended exposure

- **Traversal protection looks correct**: normalizes, resolves, and ensures target stays under repo-root `data/media`. See `services/api/main.py:L248-L261`.
- **Auth boundary exists**: `/media/*` requires a valid configured token (not just a role header). See `services/api/main.py:L178-L195` and `services/api/main.py:L248-L261`.

### Secrets / tokens in code, logs, fixtures, CI

- **No committed real Trade Me creds found** in `.env.example` (placeholders only). See `.env.example:L14-L20`.
- **Risk is in repo history**: earlier commits included sqlite DBs + Playwright traces/reports (can embed tokens, URLs, operator data). Evidence from commit file lists (`fd95e13`, `9440a6f`).

### Top 10 security risks (ranked)

1. **Production validation endpoint bypasses trust gate** — `services/api/main.py:L2353-L2371` calls `LaunchLock.validate_publish(..., test_mode=True)`; `retail_os/core/validator.py:L93-L103` returns early in test mode.
2. **Footgun env var enables header-based privilege escalation** — `services/api/main.py:L217-L225` (`RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES`) combined with Next proxy forwarding role headers/cookies `services/web/src/app/api/proxy/[...path]/route.ts:L20-L33`.
3. **E2E/CI may require insecure auth to pass** (based on Playwright failure when unauthenticated) — `services/web/playwright.config.ts:L38-L71` boots API/worker/web but does not configure `RETAIL_OS_*_TOKEN` values.
4. **Universal scraper uses system `curl` for “403 bypass”** — external call path via subprocess; high operational/security risk if ever used on untrusted URLs. `retail_os/scrapers/universal/adapter.py:L28-L48`.
5. **Worker swallows logging failures silently** — can hide errors/attacks; `retail_os/trademe/worker.py:L73-L100`.
6. **API startup swallows DB init failure** — app continues with partial state; can mask misconfig. `services/api/main.py:L89-L102`.
7. **RoleSwitcher presents privileged roles even when ineffective** — may lead operators to think they are “root” when backend still treats them as listing. `services/web/src/app/_components/RoleSwitcher.tsx:L6-L35` + server downgrade `services/api/main.py:L205-L225`.
8. **Proxy endpoint forwards caller-provided `X-RetailOS-Role`** — safe only if server downgrade remains enabled; otherwise becomes a privilege escalation bridge. `services/web/src/app/api/proxy/[...path]/route.ts:L20-L33`.
9. **Media proxy requires token cookie, but token values are unmanaged** — encourages copying secrets into browser cookies; risk of leakage on shared machines. `services/web/src/app/api/media/[...path]/route.ts:L18-L33`.
10. **Git history includes sensitive artifacts risk** — even if current tree is clean, merges without squashing may persist leaked data. Evidence: commit contents of `fd95e13` / `9440a6f`.

### Must-fix items (minimal patch plan)

- **Fix 1 (must)**: change `/validate/internal-products/{id}` to call `validate_publish(..., test_mode=False)` and return trust blockers normally. If you need a test bypass, gate it behind an explicit query param + CI-only env (e.g. `RETAIL_OS_ALLOW_TEST_BYPASS=1`) and default to off.
- **Fix 2 (must)**: update Playwright/CI to authenticate **without** weakening prod RBAC:
  - In CI web job, set `RETAIL_OS_POWER_TOKEN` to a random value.
  - In Playwright tests, set `retailos_token` cookie to that value before crawling protected pages.
  - Keep `RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES=false` explicitly in CI.
- **Fix 3 (must)**: ensure merge strategy does not permanently include DB/report artifacts (squash merge or rewrite history before merge).

---

## D) “Cheating / Defaults” Audit

### Findings

- **High (runtime path, NOT OK)**: Trust gate bypass in validation endpoint.
  - Evidence: `services/api/main.py:L2353-L2371` + `retail_os/core/validator.py:L97-L103`.
  - Impact: operator can see “ok” validation even when trust score fails, weakening publish readiness discipline.
- **High (test-only mechanism but dangerous if mis-set, NOT OK in prod)**: `RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES`.
  - Evidence: `services/api/main.py:L217-L225`, tests set it `tests/test_schema_and_media.py:L105-L224`.
  - Impact: if enabled, any client can claim `X-RetailOS-Role: root` and become root.
- **Medium (tests, gives false confidence)**: UI framework test intentionally does not fail on console errors.
  - Evidence: `services/web/tests/framework.spec.ts:L24-L45`.
  - Impact: real regressions can ship while tests stay green.
- **Medium (operator UX “fake” role selection)**: RoleSwitcher writes `retailos_role` cookie; backend typically ignores elevated roles unless insecure env is enabled or token matches.
  - Evidence: `services/web/src/app/_components/RoleSwitcher.tsx:L21-L26` + `services/api/main.py:L215-L225`.
  - Impact: “tests passed / looked fine” while operators are actually unauthenticated.
- **Low (error hiding)**: API startup doesn’t crash on DB init failure.
  - Evidence: `services/api/main.py:L95-L102`.
  - Impact: can convert hard failures into confusing partial failures.

---

## E) Functional Duplication & Wrong Placement (Operator simplicity)

### Duplicates / confusing exposures

- **Pipeline vs Bulk Ops** (same intent: run scrape/enrich/dry-run/publish at scale).
  - **Decision**: **Keep** `/pipeline` as primary; **Move to Advanced** `/ops/bulk`.
  - Rationale: `/pipeline` is the “single operator screen”; `/ops/bulk` is powerful and easy to misuse.
- **Commands vs Inbox** (both “what’s happening?”).
  - **Decision**: **Keep** `/ops/inbox` for operators; **Move to Advanced** `/ops/commands` (debug).
- **Role switching** (UI control implies capability).
  - **Decision**: **Remove** RoleSwitcher from the main shell; keep access only on `/access`, and show “effective role” from `/whoami`.
- **Queue page** (legacy operational surface).
  - **Decision**: **Move to Advanced** `/ops/queue` or remove if superseded; it adds another place to “do things”.

### Proposed final 5-screen operator menu (exact routes)

1. **Daily Home / Inbox**: `/` (Ops Workbench) + “needs attention” panels
2. **Run today’s pipeline**: `/pipeline`
3. **Review drafts (approve/hold)**: `/vaults/live?status=DRY_RUN`
4. **Removed items / withdrawals**: `/ops/removed`
5. **Orders**: `/orders`

Everything else should be behind an **“Advanced / Admin”** section:
`/ops/bulk`, `/ops/commands`, `/ops/audits`, `/admin/settings`, `/ops/trademe`, `/ops/llm`, `/ops/readiness`, `/fulfillment/*`.

---

## F) Business Guardrails Audit (Money-impact correctness)

### Publish flow (dry-run → approve with drift lock)

- **PASS (strong)**: approve publish enforces:
  - Trade Me credentials must be valid (`TradeMeAPI()` init) `services/api/main.py:L1174-L1180`
  - store mode must not be HOLIDAY/PAUSED `services/api/main.py:L1181-L1187`
  - optional daily publish quota `services/api/main.py:L1188-L1215`
  - drift lock between DRY_RUN and approve (`supplier_snapshot_hash`) `services/api/main.py:L1264-L1271`
  - LaunchLock readiness required with `test_mode=False` `services/api/main.py:L1273-L1284`

### Reprice flow

- **FAIL (missing guardrails)**:
  - There is an `UPDATE_PRICE` command generator (`retail_os/core/inventory_ops.py:L13-L63`) and a Trade Me API update call exists in `retail_os/trademe/api.py` (unit-tested), but there is **no operator preview/confirm/bounds enforcement surface** in the API/UI.
  - Minimal fix: add “preview reprice” endpoint returning counts + sample diffs; require explicit confirm with min/max bounds and margin validation (reuse `PricingStrategy.validate_margin`).

### Duplicates flow

- **FAIL (not present in this slice)**: no clear “preview keep-rule → withdraw duplicates safely” operator path found in current API surface.
  - Minimal fix: add a read-only duplicates report endpoint + a confirm endpoint that enqueues withdrawals with a dry-run preview first.

### Withdraw removed flow

- **PARTIAL (guardrails missing)**:
  - Backend endpoint exists `/ops/bulk/withdraw_removed` and is power-gated. `services/api/main.py:L1132-L1147`.
  - **Missing**: confirmation step with count preview, and “do not enqueue duplicates if already pending”. Current `withdraw_unavailable_items` blindly enqueues. `retail_os/core/inventory_ops.py:L65-L97`.

---

## G) Test Suite Quality Audit (Not just coverage %)

### What I ran locally

- **pytest**: `python3 -m pytest tests -q` ✅ (12 passing; `pytest.ini` excludes `@live`)
- **web build**: `npm --prefix services/web run build` ✅
- **Playwright smoke**: `npx playwright test --grep @smoke` ❌ (fails link integrity due to missing auth + broken doc link)

### Determinism / isolation / external calls

- **Pytest**: marked `live` tests are excluded by default (`pytest.ini:L1-L7`), so CI won’t hit supplier sites or Trade Me.
- **Playwright**: workflow tests that “hit real external systems” are opt-in (`services/web/tests/workflows.spec.ts:L24-L28`), which is good.
- **Big gap**: there is no deterministic DB seeding step visible in current CI (`.github/workflows/ci.yml:L88-L94` runs Playwright without a seeder).

### 5 strong tests (they catch real regressions)

1. **DB migration regression**: adds missing columns to old sqlite schemas (`tests/test_schema_and_media.py:L15-L70`).
2. **/media URL mapping**: prevents broken image URLs and accidental exposure (`tests/test_schema_and_media.py:L73-L81`).
3. **Draft payload endpoint won’t 500 on blocked items**: protects operator UX and debuggability (`tests/test_schema_and_media.py:L212-L267`).
4. **Trade Me API init requires creds**: prevents accidental “offline success” (`tests/test_trademe_api_unit.py:L40-L48`).
5. **Link integrity crawler**: in principle, catches broken internal navigation and SSR crashes (`services/web/tests/links.spec.ts:L8-L101`) — currently failing, which is useful signal.

### 5 weak tests (false confidence risk)

1. **Framework exercise does not fail on console errors** (`services/web/tests/framework.spec.ts:L24-L45`).
2. **Missions “page loads” do not assert authenticated data/controls** (headings can render while backend is 403’ing).
3. **“root role” header usage in Playwright API calls is misleading**; server normally downgrades role headers (`services/web/tests/missions.spec.ts:L72-L118` + `services/api/main.py:L215-L225`).
4. **No E2E assertions on request payload shapes for destructive actions** (publish/withdraw/reprice) unless live mode is enabled.
5. **No CI proof that Pipeline works under correct auth** (Pipeline pages crash without Power auth; see `services/web/src/app/pipeline/[supplierId]/page.tsx:L21-L22`).

### Flaky / nondeterminism risks

- Link crawler is deterministic, but **it requires stable auth + seed data**; without that it fails for the wrong reason (403/500).
- Next dev origin warning suggests future brittleness in Next dev server configuration (observed during Playwright run).

---

## H) CI Workflow Audit

File: `.github/workflows/ci.yml`

### CI correctness verdict

**NEEDS FIXES**

- **Missing web build step** in the `web` job; only lint + Playwright runs. Add `npm run build` before Playwright.
- **No explicit auth/seeding for Playwright**: CI sets `RETAILOS_E2E_DATABASE_URL` but does not configure `RETAIL_OS_POWER_TOKEN` nor set cookies for tests, so protected routes can 403/500 (matches local Playwright failure).
- **External call prevention**: Python tests exclude `@live` by default (good). Playwright “live flow” is opt-in (good). Still, consider a hard CI env guard (e.g. `RETAILOS_DISABLE_EXTERNAL=1`) enforced inside `TradeMeAPI` and scrapers.
- **Artifacts**: Playwright reports are uploaded on failure/success (good): `.github/workflows/ci.yml:L95-L109`.

### Minimal fixes

- Add `npm run build` to web job before Playwright.
- Add an explicit CI-only token setup:
  - `RETAIL_OS_POWER_TOKEN: ${{ secrets.CI_POWER_TOKEN }}` (or generate per run)
  - In Playwright tests, set `retailos_token` cookie prior to visiting protected pages.
- Explicitly set `RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES=false` in CI env to prevent accidental escalation.

---

## I) Final Recommendations

### Must-fix before merge (max 10)

- **Remove trust bypass from production validation endpoint** (`services/api/main.py:L2353-L2371`).
- **Make Playwright auth deterministic without weakening prod RBAC** (CI token + test cookie).
- **Fix broken internal doc link** (`services/web/src/app/access/page.tsx:L14-L16`) by either adding a `/docs/...` route or linking to a real served location.
- **Prevent duplicate withdraw enqueues** in `withdraw_unavailable_items` by skipping if a pending `WITHDRAW_LISTING` already exists for that listing id.
- **Add “count preview + confirm” UX** before bulk withdraw to avoid one-click mass destructive actions.
- **Decide merge strategy for artifact-heavy commits** (squash or rewrite history) to avoid embedding DB/traces in main history.
- **Tighten/clarify RoleSwitcher** so it cannot imply privilege without a token (or remove from main nav).
- **Add web build step to CI** before Playwright.
- **Add CI hard guard against external calls** (defensive env + code checks) to protect against future “seed” scripts drifting into network usage.
- **Document the intended RBAC model** (token-required for Ops/Media; header roles dev-only) in one operator-facing page.

### Nice-to-have (max 10)

- Replace FastAPI `@app.on_event("startup")` with lifespan handlers (deprecation).
- Update SQLAlchemy legacy `Query.get()` usage (`retail_os/core/listing_builder.py:L24-L27`).
- Add explicit reprice preview/confirm endpoints with bounds and margin rules.
- Add a duplicates preview/confirm flow (withdraw safely with dry-run).
- Remove/relocate `UniversalAdapter` “curl bypass” behind explicit “advanced tooling” guardrails.

### “Merge readiness” checklist (pass/fail)

- **Auth bypass cannot leak into prod by accident**: **FAIL** (validation endpoint bypass + insecure env footgun not hardened in CI)
- **Seed/E2E deterministic and offline**: **FAIL** (no seeding step; Playwright fails without auth)
- **Tests fail on real regressions**: **PARTIAL** (good unit/contract tests; some UI tests are weak / currently failing)
- **Operator menu simple; duplicates controlled**: **PARTIAL** (Pipeline direction is good; bulk/queue still exist; duplicates flow not clearly implemented)
- **CI runs end-to-end with artifacts**: **PARTIAL** (artifacts upload good; missing build + missing auth/seeding)

