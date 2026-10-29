---
name: hf-model-fetch
description: "How setup finds, screens and pins the pretrained models and companion datasets a task allows from the hub: the search, the permissions that are separate questions, the size by measured memory, the screening of companion data against every protected split, and the local pin under prepared/. Use in setup, before the first experiment, when the task grants hub access."
---
# Fetching models and data from the hub

Three permissions are separate questions, each answered by the task
statement: may the task use pretrained models from a hub, may it use
external data, may it look at others' solutions to this task. Hub access
alone grants the first; nothing here assumes the other two.

- Search the hub for models specific to the problem (the task type, the
  modality, the domain), and, where the task permits solution lookup,
  public code and competition write-ups for winning methods on similar
  problems; after similarity, prioritise winners.
- Shortlist a handful of models (two to five), each with its name, its
  revision, a line on what it is, its parameter count and the memory it
  needs at the task's batch size, measured, not assumed; size to the
  task's compute. A companion dataset only when the task permits external
  data.
- Screen a companion dataset before it trains anything: no overlap with
  the task's validation or test rows, no near-duplicates of them, nothing
  dated after a temporal cutoff, and a licence the task allows. Record
  what was checked and how.
- Download the shortlisted weights and the screened data in setup, pinned
  by revision, under `prepared/models/` and `prepared/data/`, and record
  the local path of each beside its name in the domain statement.
  Implementation and verification have no web: a model is loaded from its
  pinned path, and a load that fails is an error, not a fallback.
- Deduplicate across everything found before recording; one shortlist.
