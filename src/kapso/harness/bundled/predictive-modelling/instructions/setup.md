# Setup

Pin what every later session will see, then write the domain statement. Do
not train a model in setup.

1. Read the task's data reference and the evaluation's contract. Profile the
   data: the tables and their keys, row counts, the time range, the label's
   definition and base rate, the columns the evaluation strips, the
   modality of each input (text, image, audio, time series).
2. When the data is a relational database with a temporal cutoff, verify
   the sanitized copy the task statement names (row counts against the
   cutoff, the test table's columns, the tree read-only); build one with
   the sanitized-copy skill's script only when the task provides none.
   Check it against the regime the task statement names (the
   temporal-protocol skill has both).
3. When the task grants hub access, find the candidate pretrained models
   and companion datasets with the hf-model-fetch skill and record the
   shortlist.
4. Start the two files the living-documents skill describes: the table
   information file with what the profile found, the feature history file
   empty.
5. Write the domain statement: the task type and modality; the metric with
   its direction; the splits with their sizes and time spans; the label's
   base rate; the regime, in the temporal-protocol skill's words; the
   prediction contract (what to write, where, in what order); the compute
   (GPU, CPUs, memory); the data's size and the stage it implies (the
   ideation page); what the task grants (hub access, hosted model APIs,
   external data under its leakage rule); the model shortlist; and the
   relbench-api skill's traps that apply to this data's library.
