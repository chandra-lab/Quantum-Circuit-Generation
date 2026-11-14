# Research runs

`python -m research train` writes one directory per run here, named `<config name>-<UTC timestamp>` unless `--run-dir` is given. Everything in this folder except this file is git-ignored.

Each run contains:

- `config.json`: every hyperparameter used, reloadable with `--config`
- `checkpoints/best.pt` (best validation epoch) and `checkpoints/last.pt`
- `scaler.json`: feature means and scales, fitted on the training split only
- `label_map.json`, `features.json`
- `history.csv` and `loss_curve.png`: per-epoch train/validation loss, validation accuracy and macro F1
- `metrics.json`: validation and test accuracy, macro and per-class precision/recall/F1, confusion matrices
- `confusion_matrix_{val,test}.csv`, `per_class_{val,test}.csv`
- `evaluation_<checkpoint>.json`, written by `python -m research evaluate`
