# How it works

1. Installation adds a marked instruction block to the workspace's `AGENTS.md`.
2. The block directs the agent to read the generated skill index and load a matching skill.
3. The Python gateway dispatches commands from `tools/registry.json`. The local MCP server uses the same gateway.
4. Checkpoints and the error ledger preserve short handoffs and records of failures. SQLite FTS5 makes local notes and receipts searchable.

## Components

| File | Responsibility |
| --- | --- |
| `tools/gateway.py` | Dispatch registered commands, validate inputs, and retry selected failures. |
| `tools/mcp_server.py` | Expose the registered tools over standard input and output. |
| `tools/verify_all.py` | Exercise the bundled tools in a test workspace. |
| `tools/checkpoint.py` | Store and retrieve one active task checkpoint. |
| `tools/ctx_search.py` | Index and search local history with SQLite FTS5. |
| `tools/error_ledger.py` | Track failures and suggest rules from recurring issues. |
| `tools/fanout.py` | Run registered commands in parallel with optional file locks. |
| `tools/watchdog.py` | Inspect workspace state for problems. |
| `tools/code_lens.py` | Inspect Python code using its abstract syntax tree. |
