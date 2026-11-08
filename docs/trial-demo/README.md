# stats-demo (trial baseline)

A tiny, deliberately buggy Python project used by the
[end-to-end trial guide](../trial-guide.md).

```text
src/stats.py        # total(), mean(); mean() is wrong on purpose
tests/test_stats.py # the behavior the implementation should satisfy
```

Copy this directory to a fresh workspace, make it a Git repository, then install
cc-Harness into it:

```sh
# from the cc-Harness checkout
bash install.sh "<trial-workspace>"
# or, on Windows:
powershell -ExecutionPolicy Bypass -File install.ps1 -Target "<trial-workspace>"
```

Run the tests from the trial workspace:

```sh
python -m unittest discover -s tests -v
```

Two tests fail on the initial baseline. The trial guide explains what to ask
your DSH session to fix.
