# Working Agreement — vigia_crypto / Football AI Lab

## Autonomy
Full autonomy on this project. Make file edits, run shell/git commands, and commit
without asking. Don't pause for confirmation on routine work. Permissions are already
set to bypass mode in `.claude/settings.json` — no approval prompts needed.

When the user steps away (says "going for dinner / shower / away", or starts a /loop):
- Keep working through everything that doesn't need his input.
- If a decision genuinely needs him, DON'T stop. Log it under "## Pending Decisions"
  in NOTES.md, drop a `# NEEDS_DECISION: <question>` comment at the relevant spot in
  the code, and move on to the next task.
- Only stop entirely if nothing at all can progress without him.

## Still flag first (even in full autonomy)
These stay gated because they're hard to undo or leave the machine. A 5-second
heads-up is cheaper than the mistake — this is in the user's interest:
- Dropping/truncating DB tables or deleting data
- `git push --force`, history rewrites, deleting branches
- Sending anything outward on his behalf (emails, posting/publishing content)
- Spending money

Everything else — edits, normal commits, branches, tests, builds, reads — just do it.

## Honesty about limits (not promising what I can't do)
- I can't switch my own model (Sonnet/Opus). That's the user via `/model`.
- I can't run `/compact` on myself — the harness manages context automatically.
- For any factual claim about APIs, versions, prices, or library behaviour: test it
  with a real call before stating it as fact. Build on what we've seen work, not on
  assumptions. (This is why FotMob/Sofascore/Sportmonks were ruled out empirically.)

## Project pointers
- Football AI Lab lives under `backend/Api/services/football_*.py` + the frontend at
  `frontend/src/app/football-ai-lab/`. Architecture + state notes are in the agent
  memory (project_football_lab).
- Two git remotes: push to BOTH `origin` and `deploy` (Railway). Frontend on Vercel.
