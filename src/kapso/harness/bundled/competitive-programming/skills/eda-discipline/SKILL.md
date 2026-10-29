---
name: eda-discipline
description: "What a run prints so the next session can read it: an exploration block at the start, an error-analysis block at the end, timings per stage, a debug mode that exercises the whole pipeline on a sample, and quiet logs. Use when writing or reviewing the program that trains and predicts."
---
# EDA and error-analysis discipline

A run is read by sessions that did not write it. Print what they need.

- **At the start, an exploration block:** the data directory's contents;
  sizes, shapes and a few rows with their content (not only ids); the
  label distribution; a few rows of the sample submission to fix the
  output format; what is specific to the task (token lengths, image
  shapes, audio durations, time ranges); anything suspicious that earlier
  experiments' outputs raised. The block stays stable across iterations:
  it is not what gets improved.
- **At the end, an error-analysis block:** each member's score and the
  ensemble's; the prediction distribution; wrong and poor predictions
  with their features, not only their ids; a sample of validation
  predictions beside the true labels; a few rows of the final
  submission; a confusion matrix where it reads; feature importances as
  a leakage probe (a feature that dominates is a question).
- **Timings:** a timer around every stage, printed (epochs when they are
  long); estimate the full run from the data's size and the model before
  launching it, and leave a margin for writing the predictions.
- **Debug mode:** a flag that runs the whole pipeline on a small
  stratified sample (every output type present, several rows per class),
  sampled before the train/validation split, through to the written
  predictions, with the rows it skips filled with a default; the full
  mode rewrites every prediction. Run debug first, every time.
- **Quiet logs:** warnings silenced first thing; no progress bars; no
  installation output; verbose flags off in loaders and trainers.
- **Encoding:** read and write non-ASCII text the way the sample
  submission does; follow its exact format and encoding.
