# cc-Harness

**Skills, tool routing, and task recovery for DeepSeek Harness.**

cc-Harness adds a workflow layer to [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/deepseek-harness). It provides a searchable skill index, a Python tool gateway with a local MCP server, task checkpoints, and verification helpers. DSH continues to run the agent and connect to the model.

[![self-check](https://github.com/kaihu8766-netizen/cc-Harness/actions/workflows/ci.yml/badge.svg)](https://github.com/kaihu8766-netizen/cc-Harness/actions/workflows/ci.yml)

**Status:** Early preview. The automated checks exercise the Python tools and MCP handler. A full DSH session and the installation paths need separate validation.

## What you get

| Feature | What it does |
| --- | --- |
| Skill index | Summarizes the bundled job application, document building, and deployment verification skills. Workspace instructions tell the agent when to load them. |
| Tool gateway | Runs registered tools through a common command and reports results as JSON. |
| Local MCP server | Exposes registered tools over JSON-RPC on standard input and output. |
| Checkpoint and search | Stores a short task handoff and searches local notes and receipts with SQLite FTS5. |
| Error ledger | Records tool failures and surfaces repeated issues for review. |
| Developer helpers | Includes a self-check, Python AST inspection, parallel tool execution, and a watchdog. |

## Quick start

Requires Python 3.10 or later. The Python tools use the standard library.

Clone the repository and try the tools from the checkout:

```sh
git clone https://github.com/kaihu8766-netizen/cc-Harness.git
cd cc-Harness
python tools/gateway.py list
python tools/gateway.py run checkpoint.get
python tools/mcp_server.py --selftest
```

### Install into a DSH workspace

On Windows, run the following from the checkout and substitute your actual DSH workspace path:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -Target "C:\path\to\dsh-workspace"
```

The installer backs up existing `skills/`, `tools/`, and `AGENTS.md` under `out/backup/`, copies missing files, and adds a marked instruction block to `AGENTS.md`. Run workspace commands from the target directory. To remove the instruction block, run `uninstall.ps1` with the same `-Target`. Review copied files separately before removing them.

The Bash installer is experimental. Prefer trying the tools from the checkout on macOS or Linux while installation is being validated.

### Try the tools

```sh
python tools/gateway.py skill deploy_verify
python tools/checkpoint.py set "Reviewed the failing test. Next: fix the input parser."
python tools/checkpoint.py get
python tools/ctx_search.py search "parser"
python tools/error_ledger.py stats
```

Run `python tools/verify_all.py` in a disposable checkout or test workspace. It writes test state, including the current checkpoint.

For a local MCP client, configure Python to run `tools/mcp_server.py` from the cc-Harness installation. Check client compatibility and review the registered commands before enabling tools.

## How skills and failure records work

The installer adds instructions for reading `skills/INDEX.md` and loading a matching skill. To regenerate the index, run `python tools/skills_index.py`. Use `--check` to check it against the skill files.

The gateway records final tool failures in `out/review/errors/error_ledger.jsonl`. Run `python tools/error_ledger.py learn` to review suggested rules for recurring errors. Use `--apply` when you want to append those suggestions to the discipline file.

- [How it works](docs/how-it-works.md)
- [FAQ](docs/faq.md)
- [License](LICENSE)

cc-Harness is an independent community project. Claude Code and DeepSeek Harness are referenced to describe the project's inspiration and integration. The project has no affiliation with Anthropic or DeepSeek.
