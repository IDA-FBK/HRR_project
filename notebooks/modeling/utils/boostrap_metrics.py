import numpy as np
# This module implements bootstrap resampling to estimate the mean and standard deviation of various performance metrics for a given model and test set.
N_BOOTSTRAP  = 1000
RANDOM_STATE = 42
rng = np.random.default_rng(RANDOM_STATE)
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
    roc_auc_score,
    average_precision_score
)


def bootstrap_metrics(model, threshold, X_test, y_test, n_bootstrap=N_BOOTSTRAP):
    scores = {m: [] for m in ["acc", "prec", "rec", "f1", "f2", "roc_auc", "pr_auc"]}

    pos_idx = np.where(y_test.values == 1)[0]
    neg_idx = np.where(y_test.values == 0)[0]

    for _ in range(n_bootstrap):
        boot_idx = np.concatenate([
            rng.choice(pos_idx, size=len(pos_idx), replace=True),
            rng.choice(neg_idx, size=len(neg_idx), replace=True),
        ])
        X_b = X_test.iloc[boot_idx]
        y_b = y_test.iloc[boot_idx]

        y_pr = model.predict_proba(X_b)[:, 1]
        y_pd = (y_pr >= threshold).astype(int)

        try:
            scores["acc"].append(accuracy_score(y_b, y_pd))
            scores["prec"].append(precision_score(y_b, y_pd, zero_division=0))
            scores["rec"].append(recall_score(y_b, y_pd, zero_division=0))
            scores["f1"].append(f1_score(y_b, y_pd, zero_division=0))
            scores["f2"].append(fbeta_score(y_b, y_pd, beta=2, zero_division=0))
            scores["roc_auc"].append(roc_auc_score(y_b, y_pr))
            scores["pr_auc"].append(average_precision_score(y_b, y_pr))
        except ValueError:
            continue

    return {k: (np.mean(v), np.std(v)) for k, v in scores.items()}