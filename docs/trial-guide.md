# End-to-end trial guide (preview candidate)

This guide lets a first-time user install cc-Harness into a disposable Git
repository and run one real DSH session plus one follow-up session. It is the
acceptance path for the **preview candidate** release; formal release waits for
independent trial results.

## Tested environment

| Item | Value |
| --- | --- |
| DSH | **0.2.2-rc.1** (desktop) |
| Model | Native DeepSeek: provider `deepseek-account`, model `deepseek-flash` |
| Python | 3.10 or later (standard library only) |
| Installer | Windows PowerShell and Linux Bash (both exercised by CI) |
| macOS | Not tested |

Use placeholders as-is: `<cc-harness-checkout>` is the cloned repository and
`<trial-workspace>` is the disposable project directory.

## 1. Create the trial workspace

```sh
git clone https://github.com/kaihu8766-netizen/cc-Harness.git <cc-harness-checkout>
cp -r <cc-harness-checkout>/docs/trial-demo <trial-workspace>
cd <trial-workspace>
git init
git add .
git commit -m "initial trial baseline"
```

PowerShell equivalents for the copy step:

```powershell
Copy-Item -Recurse "<cc-harness-checkout>\docs\trial-demo" "<trial-workspace>"
```

`<trial-workspace>` now contains `src/stats.py` with an intentionally wrong
`mean()` and `tests/test_stats.py` describing the expected behavior.

## 2. Install cc-Harness into the trial workspace

From `<cc-harness-checkout>`:

```sh
bash install.sh "<trial-workspace>"          # Linux / macOS
```

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -Target "<trial-workspace>"   # Windows
```

Expected results:

1. The installer prints copied `skills/` and `tools/` counts and creates (or
   appends) one marked workflow block in `<trial-workspace>/AGENTS.md`.
2. From `<trial-workspace>`:

   ```sh
   python tools/check_install.py
   python tools/verify_all.py
   ```

   `check_install.py` should print **11/11 PASS**. `verify_all.py` should print
   **16/16 PASS** and must not modify your checkpoint, search index, error
   ledger, or temp files (it uses a disposable state directory).

If the installer finds a duplicated, incomplete, or misordered rule block it
exits non-zero **before** changing anything. That is expected behavior; run
`python tools/check_install.py` to see the exact problem.

## 3. Initial task in your DSH session

Open DSH with `<trial-workspace>` as the workspace, then paste this prompt:

> Read `AGENTS.md` and `skills/INDEX.md`. The statistics helpers in this
> repository are wrong: `python -m unittest discover -s tests -v` currently
> fails. Find the implementation bug and fix it so all existing tests pass
> without changing test expectations. Then record a task checkpoint with
> `python tools/checkpoint.py set "<short status + next step>"`. Report the
> commands you ran and the test output.

Acceptance criteria:

| Check | Expected |
| --- | --- |
| Tests | `python -m unittest discover -s tests -v` → **3/3 pass** (`test_total`, `test_mean`, `test_mean_empty`) |
| Checkpoint | `python tools/checkpoint.py get` returns a non-empty one-line note |
| Explanation | The session identifies that `mean()` divides by `len(values) + 1` and does not handle empty input |

On the untouched baseline the suite reports two failures (`test_mean` and
`test_mean_empty`). That failing state is what the session has to diagnose.

## 4. Follow-up in a new DSH session

Start a **fresh** session on the same workspace without pasting the previous
conversation or the checkpoint text. Use this prompt:

> Read `AGENTS.md` and the repository state, including
> `python tools/checkpoint.py get`. Carry out the next step the checkpoint
> describes. Keep the existing tests green, add tests for the new behavior, and
> update the checkpoint when the work is done. Report the commands and the test
> output.

Expected results: the session reads the checkpoint, implements
`median(values)` (empty input raises `ValueError`, odd length returns the middle
element, even length averages the two middle elements), extends the tests, and
updates the checkpoint. All tests must pass. The reference run added five median
tests (odd, even, empty, single element, unsorted input) and reported **8/8**;
covering the three required behaviors is the acceptance bar.

## Recorded acceptance run (sanitized)

This is the preview-candidate evidence, with no account details, API keys, or
machine-specific paths:

| Step | Recorded result |
| --- | --- |
| Environment | DSH 0.2.2-rc.1, provider `deepseek-account`, model `deepseek-flash`, PowerShell installer |
| Baseline | `python -m unittest discover -s tests -v` → 2 failures, exit 1 |
| Install | Installer exit 0; `check_install.py` → 11/11 PASS; `verify_all.py` → 16/16 PASS |
| Initial session | Found the `mean()` bug from the tests, fixed it, tests → 3/3 PASS, wrote a one-line checkpoint |
| Fresh follow-up session | Started with no prior summary; read `README.md`, `AGENTS.md`, and `python tools/checkpoint.py get`; added `median()` plus five tests; tests → 8/8 PASS; updated the checkpoint |
| Scope of that evidence | CLI install plus an automated, separate DSH sub-agent session. A manually opened GUI follow-up session remains unverified. |

## Verification status

| Path | Status |
| --- | --- |
| CLI install (Windows PowerShell / Linux Bash) | Verified by CI and local runs |
| Fix `mean()` in a DSH session with native DeepSeek | Verified on 2026-11-08 (cc-Harness `c3ccd4f`) |
| Separate follow-up session reads the checkpoint and adds `median()` | Verified with an automated DSH sub-agent session, not a manually opened GUI session |
| **Manual follow-up session created by a human in DSH** | **Not verified — this is what we want from trial users** |
| macOS install | Not verified |

The recorded acceptance run is sanitized: it contains no API keys, account
information, or machine-specific absolute paths. It used the same model route
(provider `deepseek-account`, model `deepseek-flash`), the same installer, and the
same demo project shipped in `docs/trial-demo/`.

## Reporting a trial

When reporting back, include only:

1. DSH version and model shown by your session.
2. The install command used (Bash or PowerShell) and the `check_install.py` result.
3. Test output for the first and follow-up sessions.
4. Whether the follow-up session found the next step from the repository and
   checkpoint alone.
5. Any place where the agent needed a hint you did not want to give.

Please do not include credentials, account details, or machine-specific paths in
reports or logs.
