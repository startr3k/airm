#!/usr/bin/env python
"""Entry point for the eval harness: `python backend/evals/run_evals.py --model <id>`.

The implementation lives in `mindforge_assess.evals` so the scoring is importable by the
tests and by the API without running anything.
"""

from mindforge_assess.evals.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
