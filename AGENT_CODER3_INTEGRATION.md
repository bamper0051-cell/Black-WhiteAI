# AGENT_CODER3 integration notes

## Added files
- `agent_coder3.py`
- `coder3/engine.py`
- `coder3/planner_adapter.py`
- `coder3/tools_adapter.py`
- `coder3/modes.py`
- `coder3/autofix.py`
- `coder3/reporting.py`
- `coder3/session_state.py`
- `coder3/prompts.py`

## Telegram callbacks
- `agent_code3_start`
- `coder3:quick`
- `coder3:autofix`
- `coder3:project`
- `coder3:review`
- `coder3:sandbox`

## Commands
- `/agent_coder3`
- `/coder3`

## Flow
1. User opens AGENT_CODER3 menu.
2. Chooses mode.
3. Bot saves `coder3_input:<mode>` into `_wait_state`.
4. User sends task.
5. `agent_coder3.run_agent_coder3()` calls `coder3.engine.run_agent_coder3()`.
6. Engine builds plan, executes direct coder flow, returns structured report.
