# Setup

Pin what every later session will see, then write the domain statement. Do
not train a model in setup.

1. Read the task's data reference and the evaluation's contract. Profile the
   data: the tables and their keys, row counts, the time range, the label's
   definition and base rate, the columns the evaluation strips, the
   modality of each input (text, image, audio, time series), the unit that
   repeats across rows (an entity, a document, a speaker, a session).
2. When the data is a relational database with a temporal cutoff, verify
   the sanitized copy the task statement names against the sanitized-copy
   skill's contract (row counts against the cutoff, the columns removed,
   the test table's columns, the tree read-only); when the task provides
   none, build one with the skill's script (a relational benchmark dataset)
   or by the contract (any other database) under `prepared/`. Check it
   against the regime the task statement names (the temporal-protocol
   skill has the three).
3. When the task grants hub access, find the candidate pretrained models
   and companion datasets with the hf-model-fetch skill, download the
   weights the statement allows under `prepared/models/`, and record the
   shortlist with each one's local path and revision.
4. Create the two files the living-documents skill describes in the shared
   artifact directory the task statement names, only when they are absent:
   the table information file with what the profile found, the feature
   history file empty.
5. Write the domain statement: the task type and modality; the metric with
   its direction and the units a published bar is quoted in; the splits
   with their sizes and time spans; the label's base rate; the regime, in
   the temporal-protocol skill's words; the prediction contract (what to
   write, where, in what order); the compute (GPU, CPUs, memory) and
   whether a full-data run fits the per-run time the task gives (the
   ideation page's stage rule); what the task grants (hub access, hosted
   model APIs, external data under its leakage rule); the model shortlist;
   the repeated unit the folds must group by; and the relbench-api skill's
   traps, which apply when the data comes through that library.
