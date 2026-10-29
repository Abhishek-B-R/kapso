---
name: hf-model-fetch
description: "How to find the pretrained models and companion datasets on the hub that fit a task, in setup, and what to record about them: the search, the size rule, the winners' methods, the deduplication. Use in setup, before the first experiment, when the task grants hub access."
---
# Finding models and datasets on the hub

In setup, when the task statement grants hub access, search for what the
task's modality and output need and record the result in the domain
statement, so every later session starts from the same shortlist.

- Search the hub for models and datasets specific to the problem (the task
  type, the modality, the domain), and search public code and competition
  write-ups for winning methods on similar problems; after similarity,
  prioritise winners.
- Return a handful of models (two to five) and the companion dataset when
  one exists; when nothing specific exists, the most downloaded model of
  the task type. Keep both a model and its dataset when both apply.
- Size to the compute: a model that fits the task's GPU with room to
  fine-tune, in the low billions of parameters at most on a single card;
  no companion dataset when the task's own data is already large.
- Deduplicate across everything found before recording; one shortlist,
  each entry with its name, a line on what it is, its parameter count and
  a usage snippet.
- A companion dataset used for augmentation is used whole; the task's own
  test split is never part of any training, whatever the companion holds.
- Nothing is fetched during implementation or verification: the shortlist
  is setup's; the weights are loaded from it by name.
