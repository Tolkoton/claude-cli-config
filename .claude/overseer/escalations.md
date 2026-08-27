# Overseer escalations log

Records every PRODUCT_DECISION / BLOCKER_CLASSIFICATION / DESIGN_FORK /
ADR_RATIFICATION escalation and the human's resolution. Used in the
2-week audit to tune escalation thresholds.

## Entry format

```
## <ISO timestamp UTC> — <category> — <slice slug>
- Question: <text>
- Options offered: <list>
- Recommendation: <overseer's pick + one-line rationale>
- Human chose: <final decision>
- Latency to decision: <minutes/hours>
- Notes: <if human changed mind, if recommendation was wrong, etc.>
```

## Audit signal interpretation (re-read at the 2-week mark)

- **Human waved through immediately, picked recommendation as-is** → next
  time, this class of question can likely be handled without escalation.
  Propose change in audit.md.
- **Human reversed the recommendation** → overseer is over-confident on
  this class. Tune the check prompt; consider weakening the recommendation
  language.
- **Human deliberated long, chose other** → correct escalation, healthy
  use of human time.

---

## Second entry format — AUTONOMOUS two-way-door decisions

The format above has no slot for a decision the AI made itself: every field
(`Human chose`, `Latency to decision`) presumes a human answered. But CLAUDE.md's
verdict routing says a two-way door is *logged here and continued*, not
escalated. A decision with nowhere to be recorded stays open in working memory
and gets re-raised turn after turn, which is a stop wearing a question mark.
That happened for real on node S3 — decided once, re-surfaced to the owner three
times, never written down. Hence this second shape:

```
## <ISO timestamp UTC> — AUTONOMOUS — <item id>
- Decision: <what was decided, in one line>
- Door: two-way
- Cost to reverse: <concretely, what it would take>
- Why not escalated: <which Article 5 test it passes>
- Evidence: <what made this the right call>
- Falsified by: <the observation that would make this wrong>
- Status: CLOSED
```

**CLOSED means closed.** Once an entry exists here, the decision is not an open
question. Re-raising it with the owner is not diligence — it is an illegitimate
stop, because it asks a human to ratify something Article 5 assigns to the AI.
If new evidence genuinely falsifies it, append a NEW entry that supersedes this
one; do not reopen the old one in conversation.

---

## 2026-08-27T19:45:00Z — AUTONOMOUS — S3
- Decision: reopened DAG node S3 from `done` to `todo`, preserving its previous
  evidence under `prior_evidence` rather than overwriting it.
- Door: two-way
- Cost to reverse: one JSON edit. Nothing was built on the reopening, and the
  original evidence was never destroyed, which is what kept it two-way.
- Why not escalated: not a product decision, not a threshold, not a public
  contract, not irreversible data. Article 5 assigns it to the AI.
- Evidence: the owner's instruction named S3 as "the next ready node", but S3
  was `done`. Its OWN recorded evidence admitted the gap -- `format-on-edit.sh`
  was never actually exercised because `ruff` is absent, so the passing
  observation proved nothing. Reopening made the instruction coherent instead of
  contradicting it. Vindicated: the session then found four real defects there.
- Falsified by: the owner saying they meant a different S3, or that the prior
  evidence was in fact complete.
- Status: CLOSED
