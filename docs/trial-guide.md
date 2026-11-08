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

## 1. Create the trial workspace

Run **one** of the following blocks from start to finish in any writable
directory. Each block keeps the cc-Harness checkout and the trial workspace in
separate, disposable folders.

**Bash (Linux / macOS; run from any writable directory):**

```sh
CC_SRC="$HOME/cc-harness-src"
TRIAL="$HOME/cc-harness-trial"
rm -rf "$CC_SRC" "$TRIAL"
git clone https://github.com/kaihu8766-netizen/cc-Harness.git "$CC_SRC"
cd "$CC_SRC"
cp -r docs/trial-demo "$TRIAL"
cd "$TRIAL"
git init -b main
git add .
git commit -m "initial trial baseline"
```

**PowerShell (Windows; run from any writable directory):**

```powershell
$CC_SRC = Join-Path $HOME "cc-harness-src"
$TRIAL = Join-Path $HOME "cc-harness-trial"
Remove-Item $CC_SRC,$TRIAL -Recurse -Force -ErrorAction SilentlyContinue
git clone https://github.com/kaihu8766-netizen/cc-Harness.git $CC_SRC
Set-Location $CC_SRC
New-Item -ItemType Directory $TRIAL | Out-Null
Copy-Item ".\docs\trial-demo\*" $TRIAL -Recurse
Set-Location $TRIAL
git init -b main
git add .
git commit -m "initial trial baseline"
```

`$TRIAL` now contains `src/stats.py` with an intentionally wrong `mean()` and
`tests/test_stats.py` describing the expected behavior.

## 2. Install cc-Harness and run the installed checks

The commands below assume the variables from section 1 still exist in the same
shell. If you opened a new shell, re-create `$CC_SRC` and `$TRIAL` first.

**Bash (run from the trial workspace):**

```sh
bash "$CC_SRC/install.sh" "$TRIAL"
cd "$TRIAL"
python tools/check_install.py
python tools/verify_all.py
```

**PowerShell (run from the trial workspace):**

```powershell
powershell -ExecutionPolicy Bypass -File (Join-Path $CC_SRC "install.ps1") -Target $TRIAL
Set-Location $TRIAL
python tools/check_install.py
python tools/verify_all.py
```

Expected results:

1. Installer exit code **0**, with copied `skills/`/`tools/` counts and one
   marked workflow block in `$TRIAL/AGENTS.md`.
2. `check_install.py` exit code **0**, **11/11 PASS**.
3. `verify_all.py` exit code **0**, **16/16 PASS**.
4. Neither check leaves temporary state: `out/tmp` is absent afterwards (or
   empty if it already existed). Both tools keep disposable state under
   `out/tmp` inside the workspace, so they also work in restricted DSH
   sandboxes that deny writes outside the workspace.

If the installer finds a duplicated, incomplete, or misordered rule block it
exits non-zero **before** changing anything. That is expected behavior; run
`python tools/check_install.py` to see the exact problem.

### Verified platforms for the command blocks

| Platform | Full block run | Result |
| --- | --- | --- |
| Windows 11, PowerShell | Yes (2026-11-09) | install exit 0; `check_install` exit 0 (11/11); `verify_all` exit 0 (16/16); no `out/tmp` residue |
| Windows, Git Bash | Yes (2026-11-09) | same results as above |
| Linux Bash | Installer/self-check covered by CI; full block not run locally | CI green |
| macOS | Not run | Unknown |

## 3. Initial task in your DSH session

Open DSH with `$TRIAL` as the workspace, then paste this prompt:

> Read `AGENTS.md` and `skills/INDEX.md`. The statistics helpers in this
> repository are wrong: `python -m unittest discover -s tests -v` currently
> fails. Find the implementation bug and fix it so all existing tests pass
> without changing test expectations. Then record a task checkpoint with
> `python tools/checkpoint.py set "<status>; next: median() for odd/even/empty"`.
> The checkpoint must explicitly name the next step: implement `median()`
> covering odd, even, and empty-list cases. Keep the note under 100 characters.
> Report the commands you ran and the test output.

Acceptance criteria:

| Check | Expected |
| --- | --- |
| Tests | `python -m unittest discover -s tests -v` → **3/3 pass** (`test_total`, `test_mean`, `test_mean_empty`) |
| Checkpoint | `python tools/checkpoint.py get` returns a one-line note whose next step says to implement `median()` for odd, even, and empty lists |
| Explanation | The session identifies that `mean()` divides by `len(values) + 1` and does not handle empty input |

On the untouched baseline the suite reports two failures (`test_mean` and
`test_mean_empty`). That failing state is what the session has to diagnose.

## 4. Follow-up in a new DSH session

Start a **fresh** session on the same workspace without pasting the previous
conversation or the checkpoint text. Do not tell it what the next step is; it
must find that from the repository. Use this prompt:

> Read `AGENTS.md` and the repository state, including
> `python tools/checkpoint.py get`. Carry out the next step the checkpoint
> describes. Keep the existing tests green, add tests for the new behavior, and
> update the checkpoint when the work is done. Report the commands and the test
> output.

If the new session defaults to the `deepseek-official` route, open the model
picker and select the **DeepSeek account** provider with model `deepseek-flash`
before sending the prompt. `deepseek-official` needs an API key that a normal
account login does not provide.

Expected results: the session reads the checkpoint, implements
`median(values)` (empty input raises `ValueError`, odd length returns the middle
element, even length averages the two middle elements), extends the tests, and
updates the checkpoint. All tests must pass. The reference runs added three to
five median tests (odd, even, empty, sometimes single element/unsorted input) and
reported **6/6–8/8**. Covering the three required behaviors is the acceptance
bar.

## Restricted DSH workspace check (2026-11-09)

The self-checks used to create their disposable state in the system temp
directory, which a DSH workspace-write sandbox denies. They now create it under
`out/tmp` inside the workspace and remove it on exit.

| Test | Method | Result |
| --- | --- | --- |
| Native DSH restricted workspace | DSH 0.2.2-rc.1 CLI, `--profile headless`, `DSH_PERMISSION_MODE=workspace-write` | **Blocked before tool execution**: `ACCOUNT_SIGN_IN_REQUIRED` (the account provider needs desktop sign-in; the headless CLI cannot authenticate). No commands ran, no permission escalation, no state left. Needs a manual GUI retest in a restricted session. |
| Simulated restricted temp | `TEMP`/`TMP`/`TMPDIR` pointed at a non-directory (system temp unusable) | `check_install.py` exit **0**; `verify_all.py` exit **0** (16/16); no `out/tmp` residue |
| Repo-level regression | `tests/install_regression.py` scenario 10 | Passes: self-check works with unusable system temp and leaves no state |

## Recorded acceptance run (sanitized)

This is the preview-candidate evidence, with no account details, API keys, or
machine-specific paths:

| Step | Recorded result |
| --- | --- |
| Environment | DSH 0.2.2-rc.1, provider `deepseek-account`, model `deepseek-flash`, PowerShell installer |
| Baseline | `python -m unittest discover -s tests -v` → 2 failures, exit 1 |
| Install | Installer exit 0; `check_install.py` → 11/11 PASS; `verify_all.py` → 16/16 PASS |
| Initial session | Found the `mean()` bug from the tests, fixed it, tests → 3/3 PASS, wrote a one-line checkpoint |
| Fresh follow-up session (automated) | Started with no prior summary; read `README.md`, `AGENTS.md`, and `python tools/checkpoint.py get`; added `median()` plus five tests; tests → 8/8 PASS; updated the checkpoint |
| Fresh follow-up session (manual GUI) | A human created a new DSH GUI session on the same workspace and sent only the follow-up prompt. After switching the model picker from `deepseek-official` to `deepseek-account / deepseek-flash`, the session found the checkpoint, added `median()` plus three tests, tests → 6/6 PASS, and updated the checkpoint |
| Scope of that evidence | CLI install, one automated sub-agent session, and one manually opened GUI follow-up session. The GUI session needed one model-picker selection, not a content hint. |

## Verification status

| Path | Status |
| --- | --- |
| CLI install (Windows PowerShell / Linux Bash) | Verified by CI and local runs |
| Fix `mean()` in a DSH session with native DeepSeek | Verified on 2026-11-08 (cc-Harness `c3ccd4f`) |
| Separate follow-up session reads the checkpoint and adds `median()` | Verified with an automated DSH sub-agent session (8/8) |
| Manual follow-up session created by a human in DSH | Verified on 2026-11-09 with a fresh GUI session (6/6); it needed one model-picker selection, not a content hint |
| Native restricted workspace (DSH workspace-write) | **Not verified natively** (headless CLI cannot sign in); simulated restricted temp passed. Manual GUI retest requested |
| Independent external trial by a first-time user | **Not yet — feedback still welcome** |
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

## Troubleshooting

- **New session fails with `MISSING_CREDENTIAL ... deepseek-official`**: change
  the model picker to the DeepSeek account provider (`deepseek-account`) and
  model `deepseek-flash`; then resend the prompt.
- **Checkpoint command rejects a note**: the tool keeps one line and rejects
  notes over 100 characters. Shorten the note; on Windows, prefer passing it as
  a single quoted argument (or via Python `argv`) to avoid shell quoting issues.
- **Model provider list is empty**: sign in to the DeepSeek account in DSH
  first, then reopen the model picker.
