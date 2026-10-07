# Reproducible Revision Analysis Summary

- Human Oracle items: 1,074 across 7 source-model suites.
- Evaluators: 3; all evaluated the same items; majority vote has no binary-label ties.
- Consensus: 740 Unique and 334 Similar.
- Overall Fleiss' kappa: 0.1864.
- TF-IDF threshold 0.50: precision=0.5709, recall=0.4341, F1=0.4932, balanced accuracy=0.6434, false removals=109.
- Matched optimizer configurations with item-level metrics: 72.

The TF-IDF thresholds (0.30, 0.50, 0.70) were fixed before comparison and were not tuned to the Human Oracle.
The positive class is Similar/Removed; therefore false positives are consensus-Unique cases removed by an optimizer.
