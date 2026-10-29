# Setup

Pin what every later session will see, then write the domain statement. Do
not train a model in setup.

1. Read the task's data reference and the evaluation's contract. Profile the
   data: the tables and their keys, row counts, the time range, the label's
   definition and base rate, the columns the evaluation strips.
2. When the data is a relational database with a temporal cutoff, build the
   sanitized copy with the sanitize-cache skill's script: tables truncated at
   the cutoff, label-bearing columns removed, the test table reduced to the
   entity and its seed time. Check it against the regime the task statement
   names (the temporal-protocol skill has both) and return it as the prepared
   resource `cache`.
3. Start the two files the living-documents skill describes: the table
   information file with what the profile found, the feature history file
   empty.
4. Write the domain statement: the task type; the metric with its direction;
   the splits with their sizes and time spans; the label's base rate; the
   regime, in the temporal-protocol skill's words, and the per-tick contract
   when the regime is per-row seed time; the prediction contract (what to
   write, where, in what order); the compute (GPU, CPUs, memory); what the
   task grants (hub access, hosted model APIs, external data under its
   leakage rule); and the relbench-api skill's traps that apply to this
   data's library.
