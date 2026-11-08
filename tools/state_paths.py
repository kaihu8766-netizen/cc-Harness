# -*- coding: utf-8 -*-
"""Shared state paths for cc-Harness tools.

Self-checks and install regressions must never touch a user's real state.
Set ``CC_HARNESS_STATE_DIR`` to a disposable directory and every tool that
persists state (checkpoints, search index, error ledger, locks) writes there
instead of ``out/state`` / ``out/review/errors`` / ``out/tmp``.

With the variable unset, paths are unchanged, so normal workspace usage keeps
working exactly as before.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def override_dir():
    value = os.environ.get("CC_HARNESS_STATE_DIR", "").strip()
    return os.path.abspath(value) if value else None


def state_dir():
    override = override_dir()
    return override if override else os.path.join(ROOT, "out", "state")


def state_file(name):
    return os.path.join(state_dir(), name)


def errors_dir():
    override = override_dir()
    return os.path.join(override, "errors") if override else os.path.join(ROOT, "out", "review", "errors")


def tmp_dir():
    override = override_dir()
    return os.path.join(override, "tmp") if override else os.path.join(ROOT, "out", "tmp")
