# Proposal: advisor-facing interface

**Status: design proposal. Nothing described here is built.**

The MVP requirements list system integration as optional. We have not built an
interface, but we did think through what one should be, and the reasoning
changed how we look at the model — so it is written up rather than left as a
hallway conversation.

## What the interface is for

Our proposal argues that the value of this system is letting advisors "target
specific students rather than sending out mass-emails." That sentence describes
the interface. An advisor does not assess one student in isolation; they have a
caseload and a limited number of hours, and the question they actually face is
*which students do I contact this week*.

That framing rules out the obvious first idea. A form with one field per
feature — 36 of them — is the natural way to demo a classifier and the wrong
way to serve an advisor. Nobody types 36 values, and doing so answers a
question nobody asked.

The interface should take a roster and return a ranked list.

## Proposed screen

A single page. Upload a roster, choose what information is available, set how
many students you can realistically contact, and read off the list.

```
┌──────────────────────────────────────────────────────────┐
│  Student roster    [ upload CSV ]   or  [ use demo set ] │
│                                                           │
│  Information available:                                   │
│    ( ) At enrollment only                                 │
│    (•) Through semester 1                                 │
│    ( ) Full academic year                                 │
│                                                           │
│  Flag students above   [======|===========]   0.45        │
│                                                           │
│  ── 62 of 885 students flagged ──                        │
│  Catches 74% of students who actually drop out.           │
│  38% of those flagged would have graduated anyway.        │
│                                                           │
│  ID     Risk    Tuition    1st sem passed   Priority     │
│  4471   0.996   overdue    0 of 6           ●●●          │
│  2210   0.677   current    2 of 6           ●●           │
│  0891   0.494   overdue    4 of 6           ●            │
└──────────────────────────────────────────────────────────┘
```

## Why each control is there

**The threshold slider** is the part that matters. A model that outputs three
class labels hides the decision an advisor is really making, which is a
trade-off between missing at-risk students and wasting time on students who
were fine. Moving the slider and watching those two numbers move in opposite
directions makes that trade-off legible in a way a confusion matrix does not.
It is also the honest way to present the system: we are not claiming to know
who will drop out, we are offering a ranking and letting the user decide how
far down it to act.

**The feature-set selector** exposes our central finding. Switching from
"through semester 1" to "full academic year" adds very little predictive
performance, and switching to "at enrollment only" removes a lot. An advisor
can see for themselves that waiting for end-of-year data buys almost nothing
while costing an entire semester of intervention time.

**Ranking by probability rather than showing the predicted class** sidesteps a
real weakness. Our models are poor at identifying the "Enrolled" category, and
a three-way label would surface that weakness in the least useful place. The
operational question is who to contact first, which is a ranking problem, and
ranking by probability of dropout works regardless of how well the three-way
classification performs.

## What it would reuse

Nothing new would need training. The six fitted models are already saved to
`models/` and versioned with DVC, so any team member has them after `dvc pull`.
They return calibrated probabilities rather than bare labels, which is what
makes the ranking and the threshold possible.

The only new dependency is Streamlit itself.

## Estimated effort

| Piece | Estimate |
|---|---|
| Upload, predict, ranked table | about half an hour |
| Threshold slider with live precision and recall | about half an hour |
| Feature-set switching | fifteen minutes |

The one implementation detail worth recording is that the models expect their
columns in the order they were fitted on, which is not the order they appear in
the CSV. Reindexing on the model's own feature names avoids an error that is
easy to introduce and produces confusing failures.

## Limitations we would have to state

The precision and recall figures beneath the slider can only be computed where
the true outcomes are known, which means the held-out test set of 885 students.
Uploading a genuinely new roster would produce a ranking but no accuracy
figures, because there is nothing yet to compare against. Presenting those
numbers without that caveat would imply the system knows more about new
students than it does.

The interface would also inherit every limitation of the model behind it. A
ranking that is 74% effective at catching dropouts is useful to an advisor with
limited hours and misleading to anyone who reads it as a verdict on a student.
Any real deployment would need that framing built into the page, not left to
the documentation.
