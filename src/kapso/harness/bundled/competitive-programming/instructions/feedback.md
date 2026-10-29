# Feedback

Weigh beside the score:

- the score and the runtime against the baseline and the current best, per
  seed and overall; headroom left unspent under the time limit is a
  finding, since a contest rewards the time used;
- which algorithm family the candidate belongs to and whether that family
  is saturated with evidence (the heuristic-patterns skill names the
  families): a third annealer with new moves is not a new family;
- the category of cases where the candidate loses, never a single case:
  low performance on a kind of input is the feedback worth giving, with
  the combination of the method and the cases that shows it;
- the time to a first strong score: a candidate that shipped a valid
  solution early and improved it outranks one that scored once at the
  end;
- the floor: a candidate below the baseline the task root provides does
  not ship.
