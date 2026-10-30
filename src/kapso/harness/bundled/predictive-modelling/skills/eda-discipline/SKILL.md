---
name: eda-discipline
description: "What a run prints so the next session can read it: an exploration block at the start, an error-analysis block at the end that grows as failures emerge, timings per stage, a debug mode that exercises the whole pipeline on a sample taken inside the task's split boundaries, and logs with the noise off and the warnings on. Use when writing or reviewing the program that trains and predicts."
---
# EDA and error-analysis discipline

A run is read by sessions that did not write it. Print what they need.

- **At the start, an exploration block:** the data directory's contents;
  sizes, shapes and a few rows with their content (not only ids); the
  label distribution; a few rows of the sample submission to fix the
  output format; what is specific to the task (token lengths, image
  shapes, audio durations, time ranges); anything suspicious that earlier
  experiments' outputs raised. The block is stable in shape and grows
  when evidence warrants a new diagnostic.
- **At the end, an error-analysis block:** each member's score and the
  ensemble's; the prediction distribution; wrong and poor predictions
  with their features, not only their ids; a sample of validation
  predictions beside the true labels; a few rows of the final
  submission; a confusion matrix where it reads; feature importances as
  a leakage probe (a feature that dominates is a question). Add the
  diagnostic a failure asks for; do not remove one that answered.
- **Timings:** a timer around every stage, printed (epochs when they are
  long); estimate the full run from the data's size and the model before
  launching it, and leave a margin for writing the predictions.
- **Debug mode:** a flag that runs the whole pipeline on a small sample
  through to the written predictions, the rows it skips filled with a
  default; the full mode rewrites every prediction. The sample respects
  the task's split boundaries (grouped units stay together, time order
  stays, the test rows stay apart), is stratified for a classification
  label and spans the target's range for a regression one. Run debug
  first, every time.
- **Logs:** the noise off (progress bars, installation output, verbose
  loaders) and the warnings on: a convergence, numerical or deprecation
  warning is evidence a reader needs. Install what is missing at the top
  of the program, quietly.
- **Encoding:** read and write non-ASCII text the way the sample
  submission does; follow its exact format and encoding.
