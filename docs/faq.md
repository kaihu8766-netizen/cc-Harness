# FAQ

## Does cc-Harness improve model reasoning?

It adds workflow tools that help the agent follow project rules, verify work, and recover task state. Reasoning still comes from the model selected in DSH.

## How does it relate to Claude Code?

Claude Code inspired the skill, tool, and verification workflow. cc-Harness runs alongside DeepSeek Harness.

## Which platforms are supported?

The Python tools are checked in CI on Windows and Ubuntu. See the README for the Windows installer and the status of the Bash installer.

## What does installation change?

It copies missing skills and tools, creates example workspace files, and adds a marked block to `AGENTS.md`. Existing skills, tools, and instructions are backed up under `out/backup/`.

## Where are model calls handled?

DSH handles model selection and calls. cc-Harness supplies instructions, tools, verification, and local task state.

## How does history search work?

`ctx_search` indexes local files with SQLite FTS5 so the agent can look up relevant snippets on demand.
