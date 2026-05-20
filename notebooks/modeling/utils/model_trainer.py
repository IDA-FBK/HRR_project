import logging
import numpy as np
from sklearn.base import clone
from sklearn.metrics import fbeta_score, make_scorer, precision_recall_curve
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold

from utils.metrics import evaluate_model_performance
logger = logging.getLogger(__name__)

# Constants
RANDOM_STATE = 42
N_SPLITS = 5
BETA = 2

# Single shared drop list — used by ALL models (UIDs, dates, and other features with no value)
DROP_LIST = [
    "P_ATC_12m_before",
    "S_ATC_12m_before",
    "D_ATC_12m_before",
    "ATC_12m_before",
    "total_cost",
    "num_days",
    "num_inpatient_events",
    "entered_with_emergency",
    "is_readmitted_acute",
    "count_prior_inpatient", # has num_acute_inpatient
    "count_prior_emergency", # has 30-day window, more predictive
    "Unnamed: 0",
    "episode_id",
    "crypted_patient_id",
    "episode_start",
    "episode_end",
    "admission_month",
    "lookback_months",
    "lookahead_months",
    "episode_type",
    "is_weekend",
]
# Paths to preprocessed data for modeling; these should be the output of the `preprocess_data.py` script
DATA_PATHS = {
    "patients": "../../data/processed/modeling/patients_readmission_flag.csv",
    "episodes": "../../data/processed/modeling/inpatient_episodes.csv",
}

# Get subset of data (works for both pandas DataFrames and numpy arrays)
def _subset(data, idx):
    if hasattr(data, "iloc"):
        return data.iloc[idx]
    return data[idx]
# Get scorer for grid search based on the specified metric
def _get_scorer(metric_name):
    metric_name = metric_name.lower()
    # if threshold_metric is "f1", we can use the built-in "f1" scorer which uses beta=1 by default
    if metric_name == "f1":
        return "f1"
    # if threshold_metric is "f2", we need to create a custom scorer using make_scorer and fbeta_score with beta=2
    if metric_name == "f2":
        return make_scorer(fbeta_score, beta=BETA)

    raise ValueError(f"Unsupported threshold_metric: {metric_name}")

# Compute the specified precision-recall metric (F1 or F2) given arrays of precision and recall values
def _compute_pr_metric(metric_name, precision, recall):
    metric_name = metric_name.lower()
    with np.errstate(divide="ignore", invalid="ignore"):
        # For F1: F1 = 2 * (precision * recall) / (precision + recall)
        if metric_name == "f1":
            scores = (2 * precision * recall) / (precision + recall)
        elif metric_name == "f2":
        # For F2: F2 = (5 + precision * recall) / (4 * precision + recall), where beta=2
            scores = (5 * precision * recall) / (4 * precision + recall)
        else:
            raise ValueError(f"Unsupported threshold_metric: {metric_name}")

    return np.nan_to_num(scores)

# Select the optimal classification threshold based on the specified metric and minimum recall constraint
def _select_optimal_threshold(y_true, y_prob, min_recall, metric_name):
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    metric_scores = _compute_pr_metric(metric_name, precision, recall)
    mask = recall[:-1] >= min_recall
    if mask.any():
        best_idx = np.argmax(metric_scores[:-1][mask])
        return thresholds[mask][best_idx]

    return 0.5
# Get the names of the features used by the best model
def _get_model_feature_names(best_model, X_train):
    if "feature_selector" in best_model.named_steps:
        selector = best_model.named_steps["feature_selector"]

        if hasattr(selector, "get_feature_names_out"):
            return list(selector.get_feature_names_out())

        if hasattr(selector, "selected_features_"):
            return list(selector.selected_features_)

    if hasattr(X_train, "columns"):
        return X_train.columns.tolist()

    raise ValueError("Unable to infer feature names for fitted model.")


# Core training function
def train_and_evaluate(pipe, model_config: dict, X_train, y_train, X_test, y_test, groups_train, post_train_fn=None,):
    # Metadata from model_config
    model_name = model_config["model_name"]
    min_recall = model_config["threshold_min_recall"]
    param_grid = model_config["param_grid"]
    threshold_metric = model_config["threshold_metric"].lower()

    groups_train = np.asarray(groups_train)
    model_scorer = _get_scorer(threshold_metric)

    # Hold out one grouped fold for threshold calibration
    calibration_splitter = StratifiedGroupKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    # Split training data into grid-search and calibration subsets, ensuring no group leakage
    gs_idx, cal_idx = next(calibration_splitter.split(X_train, y_train, groups=groups_train))
    # Subset the training data for grid search and calibration
    X_gs = _subset(X_train, gs_idx)
    y_gs = _subset(y_train, gs_idx)
    X_cal = _subset(X_train, cal_idx)
    y_cal = _subset(y_train, cal_idx)
    groups_gs = groups_train[gs_idx]

    logger.info(
        f"[{model_name}] Split: {len(gs_idx)} grid-search rows / "
        f"{len(cal_idx)} calibration rows "
        f"(positive rate gs={np.mean(y_gs):.3f}, cal={np.mean(y_cal):.3f})"
    )

    # Tune hyperparameters on the grid-search subset only
    inner_cv = StratifiedGroupKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    logger.info(
        f"[{model_name}] Starting grouped grid search "
        f"(metric={threshold_metric}, min_recall={min_recall:.2f})..."
    )
    # Note: we pass groups_gs to ensure that each fold in the inner CV is also group-wise, preventing data leakage during hyperparameter tuning
    # The GridSearchCV will refit the best model on the entire grid-search subset (X_gs, y_gs) after tuning, but it will NOT use the calibration subset (X_cal, y_cal) during this process, preserving it as a truly held-out set for threshold selection.
    calibration_search = GridSearchCV(
        estimator=pipe,
        param_grid=param_grid,
        cv=inner_cv,
        scoring=model_scorer,
        n_jobs=-1,
        verbose=1,
        refit=True,
    )
    # Fit the grid search on the grid-search subset, using groups_gs to ensure group-wise splits in the inner CV
    calibration_search.fit(X_gs, y_gs, groups=groups_gs)

    calibration_model = calibration_search.best_estimator_
    logger.info(f"[{model_name}] Calibration best params: {calibration_search.best_params_}")

    # Learn threshold on a truly held-out grouped calibration fold
    cal_probs = calibration_model.predict_proba(X_cal)[:, 1]
    optimal_threshold = _select_optimal_threshold(
        y_cal,
        cal_probs,
        min_recall,
        threshold_metric,
    )

    if optimal_threshold == 0.5:
        logger.warning(
            f"[{model_name}] No threshold achieved recall >= {min_recall:.2f} "
            f"on calibration fold; falling back to 0.5"
        )
    else:
        logger.info(
            f"[{model_name}] Optimal threshold from calibration fold: "
            f"{optimal_threshold:.4f}"
        )

    # Refit the calibration-selected model on the full training set
    logger.info(
        f"[{model_name}] Refitting calibration-selected model on full training set..."
    )
    best_model = clone(pipe).set_params(**calibration_search.best_params_)
    best_model.fit(X_train, y_train)

    # Optional model-specific post-processing on the final refit model
    extra = {}
    if post_train_fn is not None:
        extra = post_train_fn(best_model, X_train)

    # Final evaluation on the held-out test set
    y_prob = best_model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= optimal_threshold).astype(int)

    default_feature_names = _get_model_feature_names(best_model, X_train)
    features_used = extra.get("selected_features", default_feature_names)

    results = evaluate_model_performance(
        y_true=y_test,
        y_pred=y_pred,
        y_prob=y_prob,
        threshold=optimal_threshold,
        model_name=model_name,
        target_recall=min_recall,
        features_used=features_used,
    )

    return {
        "best_model": best_model,
        "optimal_threshold": optimal_threshold,
        "results": results,
        "calibration_best_params": calibration_search.best_params_,
        "final_best_params": calibration_search.best_params_,
        **extra,
    }


# Model-specific post-train hooks
def logistic_post_train(best_model, X_train):
    # Extract and rank features by absolute coefficient value, applying a threshold to filter out near-zero coefficients
    classifier = best_model.named_steps["classifier"]
    coefs = classifier.coef_.flatten()
    feature_names = _get_model_feature_names(best_model, X_train)

    coef_threshold = 1e-4
    selected = [
        (feature, round(coef, 6))
        for feature, coef in zip(feature_names, coefs)
        if abs(coef) > coef_threshold
    ]

    selected.sort(key=lambda item: abs(item[1]), reverse=True)

    selected_names = [feature for feature, _ in selected]
    selected_coefs = [coef for _, coef in selected]

    logger.info(f"[logistic] Selected {len(selected_names)}/{len(feature_names)} features")
    logger.info(f"[logistic] Top 5: {selected_names[:5]}")

    return {
        "selected_features": selected_names,
        "selected_coefficients": selected_coefs,
    }