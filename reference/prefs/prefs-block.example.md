<!-- prefs:start v=2026-07-05.1 -->
**Working rules (cross-project, propagated — edit the canonical file, not this copy):**
- **Workflow:** small focused PRs; verify (lint/types/tests/build) before closing; update docs in the
  same change. Every change needs a backlog task first; mark it `in_progress` + paste the PR URL.
- **Merging:** always via branch + PR (CI must run). Never push directly to main.
- **Specs:** a task is executable only when an agent could do it without asking anything. Ambiguity
  found while executing → mark the task `blocked` with a note, don't guess.
- **Cost tiers:** deterministic script > local LLM > frontier model. Check the cheaper tier first.
<!-- prefs:local -->
**Language:** en   <!-- per-repo lines below prefs:local survive updates -->
<!-- prefs:end -->
