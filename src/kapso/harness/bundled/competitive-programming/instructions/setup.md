# Setup

Pin what every later session will see, then write the domain statement. Do
not write a solution, run the scorer or train anything in setup; the data
directory is the build's and is not changed here.

1. Read the task root: the problem statement with its examples and
   constraints, the scorer and the seed list (`kapso_datasets/seeds.txt`,
   the scorer-cli skill) or the leaderboard's descriptor
   (`kapso_datasets/contest.json`, the kaggle-cli skill), the baseline and
   its recorded scores, the quota and the deadline, the organizers' rules.
   A root built from a URL or an organizers' brief before the build follows
   the contest-preflight skill; judge the root against it and report what
   is missing in the domain statement.
2. Learn the scorer from its help, its source or its documentation and from
   the baseline's recorded output (its invocation, its output, the score's
   units and direction, the status it reports per case), or, on a
   leaderboard task, read the standings and the account's submissions list
   with the kaggle-cli skill, and check that the submission procedure the
   root names runs. When the task grants hub access, the hf-model-fetch
   skill finds and pins the pretrained models under `prepared/models/`.
3. Write the domain statement: the modality (a scorer on a seed list, or a
   leaderboard) and the problem's kind (heuristic optimisation, an exact
   algorithm, a machine-learning task under contest rules, and its twist);
   the input distribution and the largest inputs the constraints allow; the
   time and memory limits with the margin to keep; the compile and run
   lines or the kernel's fixed environment; the scorer or the board, its
   units, its direction and its rule for a failed case; whether the
   solution is randomised and how many runs a measurement takes; the seeds
   and the baseline's scores, or the standings' best and the account's
   history; the submission form, the quota with its unit and window, the
   deadline, the session limits; the compute here and on the scoring side;
   the round trip's length for the time-allocation plan; the model
   shortlist with each one's local path.
