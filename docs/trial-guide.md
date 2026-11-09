# End-to-end trial guide (developer preview)

**Status:** Developer preview — maintainer end-to-end acceptance passed; external
independent trial pending. （开发者预览版，维护者端到端已验收，外部独立试用待验证。）

This guide lets a first-time user install cc-Harness into a disposable Git
repository and run one real DSH session plus one follow-up session. Formal
release waits for independent trial results.

## Tested environment

| Item | Value |
| --- | --- |
| DSH | **0.2.2-rc.1** (desktop) |
| Model | Native DeepSeek: provider `deepseek-account`, model `deepseek-flash` |
| Python | 3.10 or later (standard library only) |
| Installer | Windows PowerShell and Linux Bash (both exercised by CI) |
| Tested commit | cc-Harness **`01b8d1e`** (clean-clone install/check runs; DSH session evidence used the same tool files) |
| macOS | Not tested |

## 1. Create the trial workspace

Run **one** of the following blocks from start to finish in any writable
directory. Each run creates a fresh, uniquely named base directory; the
cc-Harness checkout and the trial workspace live inside that base. Running the
block again never deletes or rewrites an earlier run.

**Bash (Linux / macOS; run from any writable directory):**

```sh
BASE="$(mktemp -d "$HOME/cc-harness-trial-XXXXXX")"
CC_SRC="$BASE/cc-harness-src"
TRIAL="$BASE/trial-workspace"
echo "Trial base: $BASE"
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
$BASE = Join-Path $HOME ("cc-harness-trial-" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory $BASE | Out-Null
$CC_SRC = Join-Path $BASE "cc-harness-src"
$TRIAL = Join-Path $BASE "trial-workspace"
Write-Host "Trial base: $BASE"
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

**Run these two checks from a normal PowerShell/Bash shell, not from inside a
DSH workspace-write sandbox.** The maintainer run in normal Windows PowerShell
gave `check_install.py` **11/11 PASS** and `verify_all.py` **16/16 PASS**. In a
Windows DSH workspace-write session, `check_install.py` may still fail because
SQLite cannot create its scratch state under the sandbox token.

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
   empty if it already existed).

If the installer finds a duplicated, incomplete, or misordered rule block it
exits non-zero **before** changing anything. That is expected behavior; run
`python tools/check_install.py` to see the exact problem.

### Verified platforms for the command blocks

| Platform | Full block run | Result |
| --- | --- | --- |
| Windows 11, normal PowerShell (not DSH sandbox) | Yes (maintainer, 2026-11-09) | install exit 0; `check_install` exit 0 (**11/11**); `verify_all` exit 0 (**16/16**); no `out/tmp` residue |
| Windows, Git Bash | Yes (maintainer, 2026-11-09) | same results as above |
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

Maintainer result: the initial DSH session fixed `mean()`, reported **3/3**
passing tests, and wrote a checkpoint whose next step was the `median()`
requirement above.

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
updates the checkpoint. All tests must pass.

Maintainer result for the manual GUI follow-up session: it found the follow-up
task **only from the repository and checkpoint**, implemented `median()` with
additional tests, reported **8/8** passing tests, and updated the checkpoint;
the updated checkpoint was read back successfully.

## Usage friction observed in this round

These are environment-specific observations, not general PowerShell claims.

1. **Windows DSH workspace-write blocks the two checks.**
   `check_install.py` may fail with `sqlite3.OperationalError: unable to open
   database file` when its temporary state directory lives under the sandboxed
   workspace, and `verify_all.py` may hit `PermissionError` on its scratch task
   file. There was no elevation or approval prompt. **Run both checks from a
   normal PowerShell window** (the maintainer run there passed 11/11 and 16/16).
2. **Gateway JSON arguments with spaces were split in this DSH PowerShell
   session.** Passing a checkpoint payload through
   `python tools/gateway.py run ... --json '{...}'` lost the quoting, so the
   payload was split into extra arguments; a follow-up direct attempt also hit
   the checkpoint tool's 100-character limit (104 characters). Successful
   workaround in that session: call `python tools/checkpoint.py set "<text>"`
   directly (or pass the payload via Python `argv`), keep the note at or below
   100 characters, and use `python tools/checkpoint.py get` to read it back.
   This was observed in this session's DSH/PowerShell interaction only; it is
   not attributed to every PowerShell environment.

## Restricted DSH workspace check

**Status: not supported on Windows workspace-write. Use a normal shell for
`check_install.py` / `verify_all.py`.**

Recorded maintainer retest in a DSH workspace-write session:

| Check | Exit code | Result |
| --- | --- | --- |
| `python tools/check_install.py` | **1** | 10/11 PASS; `gateway run checkpoint.get works` failed with `sqlite3.OperationalError: unable to open database file` |
| `python tools/verify_all.py` | **1** | `PermissionError` writing its scratch task file; no PASS summary printed |
| Elevation / approval | None | No UAC, no escalation, no approval prompt |
| Leftover state | Scratch directories | The process could not use or delete its own `out/tmp/cc-harness-*` directories; a normal-permission session removed them |

Environment: DSH 0.2.2-rc.1, Python 3.14, Windows, low-integrity
workspace-write token. `tempfile.mkdtemp()` directories created by that token
were unusable by the creating process even under the system temp directory.
This is a DSH sandbox/token limitation for scratch files, not a repository bug.

Workaround until a sandbox-safe self-check mode ships:

1. Run the two checks from a normal shell (outside DSH), or
2. approve one unrestricted run in DSH, or
3. use a DSH permission mode with normal workspace permissions.

## Recorded acceptance run (sanitized)

This is the developer-preview evidence, with no account details, API keys, or
machine-specific paths.

| Step | Recorded result |
| --- | --- |
| Environment | DSH 0.2.2-rc.1, provider `deepseek-account`, model `deepseek-flash`, normal Windows PowerShell, tested cc-Harness `01b8d1e` |
| Baseline | `python -m unittest discover -s tests -v` → 2 failures, exit 1 |
| Install | Installer exit 0; `check_install.py` → **11/11 PASS**; `verify_all.py` → **16/16 PASS** |
| Initial DSH session | Found the `mean()` bug from the tests, fixed it, tests → **3/3 PASS**, wrote a checkpoint naming the `median()` next step |
| Manual follow-up session | A human opened a fresh DSH GUI session without the previous summary or checkpoint text; it found the follow-up **only from the repository and checkpoint**, added `median()` plus tests, tests → **8/8 PASS**, and updated the checkpoint; the checkpoint was read back successfully |
| Scope of that evidence | Install/check commands in normal PowerShell and Git Bash; one real DSH session; one manually opened GUI follow-up session. A model-picker selection was needed when the new session defaulted to `deepseek-official`, not a content hint. |

## Verification status

| Path | Status |
| --- | --- |
| CLI install (Windows PowerShell / Linux Bash) | Verified by CI and maintainer runs |
| Fix `mean()` in a DSH session with native DeepSeek | Verified by maintainer: **3/3** |
| Fresh follow-up session reads the checkpoint and adds `median()` | Verified by maintainer: **8/8**, checkpoint updated and read back |
| Manual follow-up session created by a human in DSH | Verified by maintainer; needed only a model-picker selection, no content hint |
| Native restricted workspace (DSH workspace-write, Windows) | **Failed**: checks need normal PowerShell or an approved unrestricted run; sandbox-safe mode not implemented yet |
| Independent external trial by a first-time user | **Not yet** |
| macOS install | Not verified |

**Overall:** developer preview — maintainer end-to-end acceptance passed;
external independent trial pending. （开发者预览版，维护者端到端已验收，外部独立试用待验证。）

The recorded acceptance run is sanitized: it contains no API keys, account
information, or machine-specific absolute paths.

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
