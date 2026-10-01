# 3-minute screen-recording script

You record this yourself (phone pointed at your screen is fine, per the brief).
No slides. Screen-record two things as you talk: (1) scroll through the actual
Claude Code session that built this, and (2) the finished `dashboard.html`.
Target ~3:00. Say it in your own words — this is a guide, not a teleprompter.

---

**[0:00–0:25] What it is**
"This is the Vireo support-triage tool. The brief asked for a CSAT dashboard and
the bottom-ten agents to retrain. I built that — but the data says the real story
is a product defect, not the agents, so that's what I led with."
*(show the dashboard headline banner)*

**[0:25–1:00] The prompts / how I drove it**
"I built this AI-first with Claude Code. My first prompts were just: pull the
data files off the assignment page, then explore tickets.csv — what's the CSAT
distribution, replacements over time, who's at the bottom."
*(scroll the session to the early data-exploration commands)*
"Two things fell out immediately: replacements tripled after December, and all
the bottom agents were the Tier-2 warranty team."

**[1:00–1:40] What changed between versions**
"The classifier is where I iterated. Version one keyed on the word 'left' plus
'charge' — and scored about 80%, because customers don't talk like that. They
say 'it's a paperweight', 'the left one won't wake up', 'the right one's fine'."
*(show the gold_labels.csv and the classify.py patterns)*
"So I read more raw tickets and rewrote the patterns — including a 'right one is
fine' rule that infers the left is the broken one. That took it to 88%, and 100%
on the one label the headline depends on."

**[1:40–2:15] What I threw away**
"Two things I dropped. First, running an LLM on every ticket — I'd planned a
Haiku classifier, but Finance's email explicitly said no per-ticket model calls,
so the shipped default is the zero-cost rules; the LLM is just an opt-in. Second,
a whole pile of secondary analysis — first-contact-resolution, the SLA-credit
P&L, IVR transcript parsing — because of the five-hour cap. They're listed as
next steps, not hidden."

**[2:15–2:50] The finding + proof**
"The headline: Pulse 2 earbuds, ₹19.6 lakh of replacements since December, two-
thirds the same defect — left bud won't charge — in three manufacturing lots.
Fix the batch, not the people. And how I know it works is on the page: the
classifier accuracy and six data-quality checks, like the timezone bug that made
2,000 tickets resolve before they were created."
*(scroll to the lot table, then the 'Does it work?' panel)*

**[2:50–3:00] Close**
"Everything reproduces with one command, `python run.py`. That's it."

---
**Tips:** rehearse once; keep under 3:00; upload to Google Drive, set link
sharing to "Anyone with the link — Viewer", and paste that link into form field 8
and into SUBMISSION.md.
