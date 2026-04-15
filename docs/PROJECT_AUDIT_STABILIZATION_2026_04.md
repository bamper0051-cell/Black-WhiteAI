# Black-WhiteAI Audit (stabilization/2026-04 scope)

## 1) Architecture Breakdown

### Runtime entry points (actual)
- **Docker bot runtime:** `entrypoint.sh` → `exec python3 -u bot.py` (primary).
- **Docker admin runtime:** `docker-compose.yml` `admin_web` service → `entrypoint: ["python", "admin_web.py"]`.
- **Standalone Python entry points:**
  - `bot.py` (`if __name__ == '__main__': main()`)
  - `bot_main.py` (`if __name__ == '__main__': main()`) — appears alternate/legacy entry.
  - `admin_web.py` standalone run block exists but file currently broken by merge markers.

### Core module relationships
- `bot.py` is the orchestration hub: auth, handlers/callbacks/UI, queue, fish subsystem, admin web bootstrap, polling loop.
- `bot_main.py` imports `bot_ui`, `bot_handlers`, `bot_callbacks`, auth/config/task queue/admin web and repeats near-identical orchestration flow.
- `agent_session.py` is the “SMITH/coder” session pipeline; used by bot handlers/callbacks.
- `agent_neo.py` provides `run_neo(...)` multi-step tool pipeline (called by admin API and bot flows).
- `agent_matrix.py` provides MATRIX tool DB/planner/execution pipeline (called by admin API and bot flows).
- `agent_brain.py` defines reflexion/delegation/graph/feedback helpers but currently has no active import path from top-level runtime modules.
- `admin_web.py` provides Flask admin/mobile APIs and can invoke matrix/neo execution.
- `auth_module.py` is shared auth/profile/captcha/privilege logic for bot/admin.
- `config.py` is the active runtime config module (`dotenv` + property-based facade). `settings.py` is parallel/legacy-style config.

### Active vs dead/backup files
- **Active (runtime-mounted/executed):** `bot.py`, `admin_web.py`, `agent_session.py`, `agent_neo.py`, `agent_matrix.py`, `auth_module.py`, `config.py`, plus `bot_handlers.py`, `bot_callbacks.py`, `bot_ui.py`.
- **Likely dead/backup/legacy:** `*.pyBK`, `bot-2.py`, `admin_web_v3.py`, `admin_web_v3.pyBK`, `admin_web_v3_fixed.py`, `proj/**`, `final/**`, many duplicate archives/scaffolds.
- **Patched clones likely dead:** `bot_callbacks_patched.py`, `bot_handlers_patched.py`, `bot_ui_patched.py` (runtime imports point to originals, not patched files).

### Agent hierarchy / coordination
- User request enters Telegram flow (`bot.py`) or admin API (`admin_web.py`).
- Routing chooses agent path:
  - SMITH/session path: `agent_session.execute_pipeline(...)`
  - NEO path: `agent_neo.run_neo(...)`
  - MATRIX path: `agent_matrix.run_matrix(...)` / matrix tool API functions
- Agents use internal tool registries + sandbox subprocess execution; results/artifacts flow back to bot/admin responses.

---

## 2) Broken Components Analysis

## 2.1 Syntax/import blockers (hard failures)
- Widespread unresolved Git conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) in critical files:
  - `bot.py`, `admin_web.py`, `agent_neo.py`, `agent_matrix.py`, `auth_module.py`, `bot_ui.py`, `.env.example`, `docker-compose.yml`, `.github/workflows/build-apk.yml`, plus many Android/Dart files.
- `py_compile` fails on core runtime files above, so core runtime is non-startable in current state.
- Environment dependency gap in local run: tests fail immediately when `dotenv`/`flask` unavailable.

## 2.2 CI/build failures
- Recent Actions failures include **startup_failure/failure** before/at job setup.
- Retrieved failed job logs (run `24331632260`) show action resolution errors:
  - `Unable to resolve action actions/checkout@de0fac2e...`
  - `Unable to resolve action actions/setup-java@be666c2f...`
  - `Unable to resolve action actions/upload-artifact@bbbca2dd...`
- Workflow files themselves also contain merge markers, which can cause workflow parse/startup failures.

## 2.3 Config/env inconsistency (`config.py` / `settings.py` / `.env.example`)
- `.env.example` is corrupted by merge conflict blocks and mixes incompatible variable schemes.
- Token/key name drift:
  - `TELEGRAM_BOT_TOKEN` vs `BOT_TOKEN`
  - `GOOGLE_API_KEY` vs `GEMINI_API_KEY`
  - `JWT_EXPIRE_HOURS` vs `JWT_EXPIRY_HOURS`
  - `OLLAMA_BASE_URL` vs `OLLAMA_HOST`
- `settings.py` base path logic differs from `config.py` and appears not aligned with active runtime imports.

## 2.4 Tool registry consistency
- `agent_tools_registry.py` has 24 registered tools (unique), but config free-plan tool allowlist references names not registered there (e.g., `python_sandbox`, `chat`, `image_gen`).
- This creates permission/plan gating mismatch: valid tools may be denied or expected aliases missing.
- `agent_matrix.py` internal `_bt(...)` tool registration and `KNOWN_TOOLS` set are internally aligned, but file is currently syntax-broken due merge artifacts.

## 2.5 Manifest drift
- `MANIFEST.json` has significant drift from actual repository:
  - 195 manifest entries; 61 missing on disk.
  - References removed snapshots/paths (`BlackBugsAI_v1.0\\...`, `agent_session (1).py`, `agent_session (2).py`, etc.).
  - Includes sensitive/runtime artifacts (`.env`, multiple `.db` paths) inconsistent with a clean source manifest.

## 2.6 Database/schema mismatch risk
- Separate DB files/modules with overlapping auth/user concerns:
  - `database.py` (`automuvie.db`) contains both `news` and `users` tables (with conflicting user schemas in same module).
  - `auth_module.py`/`admin_module.py` operate on `auth.db`-style user structures.
  - `user_auth_db.py` uses separate `users_auth.db` + `web_users`.
  - `fish_db.py` uses separate fish DB schema.
- No unified migration layer; high risk of runtime mismatch and stale assumptions between modules.

## 2.7 Dead code / duplication
- `bot_callbacks_patched.py` / `bot_handlers_patched.py` / `bot_ui_patched.py` duplicate originals but are not main import targets.
- `bot.py` and `bot_main.py` duplicate orchestration logic, increasing divergence risk.

---

## 3) Prioritized Patch Plan

Priority: CRITICAL  
File: `bot.py`, `admin_web.py`, `agent_neo.py`, `agent_matrix.py`, `auth_module.py`, `bot_ui.py`, `.env.example`, `docker-compose.yml`, `.github/workflows/build-apk.yml`  
Problem: Unresolved Git merge conflict markers break parsing/runtime/CI startup. Remove markers and produce single canonical merged content per file.

Priority: CRITICAL  
File: `.github/workflows/build-apk.yml` (and other affected workflows)  
Problem: Workflow corruption + unresolved action references causing setup failures in CI. Restore valid YAML and valid action references per repo policy.

Priority: HIGH  
File: `.env.example`, `config.py`, `settings.py`  
Problem: Env var schema drift and duplicate config models. Define one canonical env contract, align names, keep backward-compatible aliases only where necessary.

Priority: HIGH  
File: `bot.py`, `bot_main.py`  
Problem: Duplicate entry/orchestration logic with divergence risk. Choose one canonical entry runtime path and reduce duplication (or make one thin wrapper).

Priority: HIGH  
File: `agent_tools_registry.py`, `config.py`  
Problem: Plan tool allowlist mismatches registered tool names. Align plan tool names/aliases with actual registry.

Priority: HIGH  
File: `database.py`, `auth_module.py`, `admin_module.py`, `user_auth_db.py`, `fish_db.py`  
Problem: Fragmented database ownership and overlapping schemas without migrations. Define DB ownership boundaries and migration strategy.

Priority: MEDIUM  
File: `MANIFEST.json`  
Problem: Manifest references missing/legacy/sensitive files. Regenerate manifest from current source tree and exclude runtime secrets/db artifacts.

Priority: MEDIUM  
File: `bot_callbacks_patched.py`, `bot_handlers_patched.py`, `bot_ui_patched.py`, `admin_web_v3.py`, `admin_web_v3_fixed.py`, `bot-2.py`, `*.pyBK`  
Problem: Dead/backup duplicates create maintenance ambiguity. Move to archive folder or remove from active root after validation.

Priority: LOW  
File: `docs/ARCHITECTURE.md`, `docs/ACTIVE_FILES.md`  
Problem: Documentation can drift from actual runtime. Update after stabilization to reflect canonical startup path and active modules only.
