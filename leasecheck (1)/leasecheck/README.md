# LeaseCheck (prototype)

Upload an off-campus lease and get red / yellow / green flags with plain-English explanations, a question to ask the landlord, and a source for each flag. Not legal advice: it points students to free help.

## Run it (about 5 minutes)

1. Install Python 3.10+.
2. In this folder, run:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Your browser opens the app. Go to **Try a sample lease**, then **Use this sample**, then **Check my lease**.

**Demo mode vs AI mode**
- With no API key, the app uses simple keyword matching. It's good enough to test the screens and demo the flow.
- For real AI review, paste an Anthropic API key in the sidebar (or set `ANTHROPIC_API_KEY`). The default model is `claude-sonnet-5-5`; change it with the `LEASECHECK_MODEL` environment variable.

## Files

| File | What it is | Who edits it |
| --- | --- | --- |
| `rules.json` | The red-flag checklist: 12 draft rules, each with severity, explanation, landlord question, and source | **Non-coders**: add, fix, and fact-check rules here |
| `samples/` | Fictional test leases: one with 12 planted problems, one clean (.txt and .pdf) | Anyone: write more test leases |
| `checker.py` | Reads the lease, runs AI or demo check, and drops any quote that isn't really in the lease | Builders |
| `app.py` | The web page | Builders and designers |

## Current results (demo mode)

- `sample_lease_problems`: 12 of 12 planted problems flagged
- `sample_lease_clean`: 0 false flags

## Next steps for the team

- [ ] Have the rules checked by someone with legal knowledge (for example, Temple Law's Landlord-Tenant Help Service) before the final pitch
- [ ] Write 3 or more extra sample leases with different wording, so the AI is tested on more than keywords
- [ ] Get an API key and compare AI mode vs demo mode on all samples: that's your catch-rate number for the pitch
- [ ] Design polish: logo, colors, mobile view

## Rules for the challenge

Use only fictional or sample leases and public information. Never upload a real person's lease.
