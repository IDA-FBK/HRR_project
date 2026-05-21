"""
Edit OUTPUT_DIR below to choose where plots and tables are saved.
"""

from pathlib import Path
import matplotlib

matplotlib.use('Agg')  # Force background rendering
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(r"./outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- HYBRID SAVE FUNCTION ---
_plot_counter = 0


def save_plot(name=None):
    """Saves all open figures. Uses a name if provided, else falls back to a counter."""
    global _plot_counter

    fignums = plt.get_fignums()
    if not fignums:
        return  # No plots to save

    for i, fignum in enumerate(fignums):
        fig = plt.figure(fignum)

        if name:
            # If there's multiple open plots but one name, append an index so they don't overwrite
            fname = f"{name}.png" if len(fignums) == 1 else f"{name}_{i + 1}.png"
        else:
            _plot_counter += 1
            fname = f"auto_plot_{_plot_counter}.png"

        filepath = OUTPUT_DIR / fname
        fig.savefig(filepath, bbox_inches="tight", dpi=300)
        plt.close(fig)
        print(f"Plot saved to: {filepath}")


# Override show so background utility functions get saved automatically
plt.show = lambda *args, **kwargs: save_plot()
# -----------------------------

# # 30-Day Readmission — Unified Model Training

# Import necessary libraries and modules
import shap
import logging
import warnings
from imblearn.ensemble import BalancedRandomForestClassifier
from catboost import CatBoostClassifier
import numpy as np
import pandas as pd
import os
import seaborn as sns
import dtreeviz
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb
import matplotlib.patches as mpatches
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.inspection import permutation_importance
from sklearn.metrics import make_scorer, fbeta_score, PrecisionRecallDisplay
from utils.feature_transformer import ClinicalFeatureSelector
from utils.train_test_split import get_train_test_split
from utils.preprocess import preprocess_features
from utils.feature_importance import get_tree_feature_importance, plot_logistic_regression_importance
from utils.model_trainer import (
    train_and_evaluate,
    logistic_post_train,
    N_SPLITS,
    RANDOM_STATE,
    DROP_LIST,
    DATA_PATHS,
)
from utils.boostrap_metrics import bootstrap_metrics
from utils.SHAP import get_shap

os.makedirs("models", exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
warnings.filterwarnings("ignore")

# ## 1. Data Loading

# Get and split the data, then preprocess features
train_df, test_df, groups_train = get_train_test_split(
    DATA_PATHS["patients"],
    DATA_PATHS["episodes"],
)

X_train, y_train = preprocess_features(train_df, cols_to_drop=DROP_LIST)
X_test, y_test = preprocess_features(test_df, cols_to_drop=DROP_LIST)

print(f"Train: {X_train.shape} | Test: {X_test.shape}")
print(f"Positive rate — Train: {y_train.mean():.3f} | Test: {y_test.mean():.3f}")
print(f"Features: {X_train.columns.tolist()}")

# ## Folds Validation

# Validate stratified group k-fold splits and check positive rates
skf = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
for i, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train, groups=groups_train)):
    rate = y_train.iloc[val_idx].mean()
    print(f"Fold {i + 1} positive rate: {rate:.3f}")

# ## 3. Logistic Regression (ElasticNet)

# Hyperparameters grid for Logistic Regression with Elastic Net regularization
LOGISTIC_PARAM_GRID = {
    "classifier__l1_ratio": [0.0, 0.1, 0.5, 1.0],
    "classifier__C": [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
    "classifier__solver": ["saga"],
    "classifier__max_iter": [5000],
}

logistic_config = {
    "model_name": "logistic",
    "param_grid": LOGISTIC_PARAM_GRID,
    "threshold_metric": "f2",
    "threshold_min_recall": 0.60,
}

logistic_pipe = Pipeline([
    ("feature_selector", ClinicalFeatureSelector()),
    ("scaler", RobustScaler()),
    ("classifier", LogisticRegression(
        random_state=42,
        class_weight="balanced",
        penalty="elasticnet",
    )),
])

logistic_output = train_and_evaluate(
    pipe=logistic_pipe,
    model_config=logistic_config,
    X_train=X_train, y_train=y_train,
    X_test=X_test, y_test=y_test,
    groups_train=groups_train,
    post_train_fn=logistic_post_train,
)

# ## 4. Decision Tree

TREE_PARAM_GRID = {
    "classifier__max_depth": [3, 4, 5, 6, 8, 10],
    "classifier__min_samples_leaf": [5, 10, 20, 30, 50],
    "classifier__criterion": ["gini", "entropy"],
}

tree_config = {
    "model_name": "decision_tree",
    "param_grid": TREE_PARAM_GRID,
    "threshold_metric": "f2",
    "threshold_min_recall": 0.60,
}

tree_pipe = Pipeline([
    ("feature_selector", ClinicalFeatureSelector()),
    ("classifier", DecisionTreeClassifier(
        random_state=42,
        class_weight="balanced",
    )),
])

tree_output = train_and_evaluate(
    pipe=tree_pipe,
    model_config=tree_config,
    X_train=X_train, y_train=y_train,
    X_test=X_test, y_test=y_test,
    groups_train=groups_train,
)

# ## 5. Balanced Random Forest

BRF_PARAM_GRID = {
    "classifier__n_estimators": [200, 400],
    "classifier__max_depth": [None, 10, 20],
    "classifier__min_samples_leaf": [1, 2, 4],
    "classifier__sampling_strategy": ["auto", 0.5],
    "classifier__replacement": [False, True],
}
brf_config = {
    "model_name": "balanced_random_forest",
    "param_grid": BRF_PARAM_GRID,
    "threshold_metric": "f2",
    "threshold_min_recall": 0.60,
}

brf_pipe = Pipeline([
    ("feature_selector", ClinicalFeatureSelector()),
    ("classifier", BalancedRandomForestClassifier(
        random_state=42,
        n_jobs=-1
    )),
])

brf_output = train_and_evaluate(
    pipe=brf_pipe,
    model_config=brf_config,
    X_train=X_train, y_train=y_train,
    X_test=X_test, y_test=y_test,
    groups_train=groups_train,
)

# ## 6. XGBoost

scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"Scale pos weight for XGBoost: {scale_pos_weight:.2f}")

XGB_PARAM_GRID = {
    "classifier__n_estimators": [200, 400],
    "classifier__max_depth": [3, 5],
    "classifier__learning_rate": [0.03, 0.1],
    "classifier__min_child_weight": [1, 5],
    "classifier__subsample": [0.8, 1.0],
    "classifier__colsample_bytree": [0.6, 1.0],
    "classifier__reg_alpha": [0, 1.0],
    "classifier__reg_lambda": [1, 10],
}

xgb_config = {
    "model_name": "xgboost",
    "param_grid": XGB_PARAM_GRID,
    "threshold_metric": "f2",
    "threshold_min_recall": 0.60,
}

xgb_pipe = Pipeline([
    ("feature_selector", ClinicalFeatureSelector()),
    ("classifier", xgb.XGBClassifier(
        objective="binary:logistic",
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        tree_method="hist",
        n_jobs=-1,
        verbosity=0,
    )),
])

xgb_output = train_and_evaluate(
    pipe=xgb_pipe,
    model_config=xgb_config,
    X_train=X_train, y_train=y_train,
    X_test=X_test, y_test=y_test,
    groups_train=groups_train,
)

# ## 7. CatBoost

CATBOOST_PARAM_GRID = {
    "classifier__depth": [4, 6, 8],
    "classifier__learning_rate": [0.03, 0.1],
    "classifier__iterations": [200, 500],
    "classifier__l2_leaf_reg": [3, 10],
    "classifier__subsample": [0.8, 1.0],
}

catboost_config = {
    "model_name": "catboost",
    "param_grid": CATBOOST_PARAM_GRID,
    "threshold_metric": "f2",
    "threshold_min_recall": 0.60,
}

catboost_pipe = Pipeline([
    ("feature_selector", ClinicalFeatureSelector()),
    ("classifier", CatBoostClassifier(
        loss_function="Logloss",
        eval_metric="PRAUC",
        auto_class_weights="Balanced",
        random_seed=42,
        verbose=0,
        allow_writing_files=False,
        thread_count=-1,
    )),
])

catboost_output = train_and_evaluate(
    pipe=catboost_pipe,
    model_config=catboost_config,
    X_train=X_train, y_train=y_train,
    X_test=X_test, y_test=y_test,
    groups_train=groups_train,
)

# ## 8. Model Comparison & Bootstrap

outputs = {
    "logistic": logistic_output,
    "decision_tree": tree_output,
    "balanced_random_forest": brf_output,
    "xgboost": xgb_output,
    "catboost": catboost_output,
}

rows = []
for name, out in outputs.items():
    r = out["results"]
    rows.append({
        "model": name,
        "threshold": round(out["optimal_threshold"], 4),
        "accuracy": round(r.get("Accuracy", float("nan")), 4),
        "precision": round(r.get("Precision", float("nan")), 4),
        "recall": round(r.get("Recall", float("nan")), 4),
        "f1": round(r.get("F1", float("nan")), 4),
        "f2": round(r.get("F2", float("nan")), 4),
        "roc_auc": round(r.get("AUC-ROC", float("nan")), 4),
        "pr_auc": round(r.get("PR-AUC", float("nan")), 4)
    })

comparison_df = pd.DataFrame(rows).set_index("model")

# SAVING TABLE
comparison_df.sort_values("f2", ascending=False).to_csv(OUTPUT_DIR / "model_comparison.csv")
print(f"Model comparison table saved to {OUTPUT_DIR / 'model_comparison.csv'}")

boot_results = {}
for name, out in outputs.items():
    print(f"  Bootstrapping {name}...")
    boot_results[name] = bootstrap_metrics(
        model=out["best_model"],
        threshold=out["optimal_threshold"],
        X_test=X_test,
        y_test=y_test,
    )
print("Done.\n")

DISPLAY_METRICS = ["acc", "prec", "rec", "f1", "f2", "roc_auc", "pr_auc"]
COL_NAMES = ["Acc", "Prec", "Rec", "F1", "F2", "AUC-ROC", "PR-AUC"]

rows = {}
for name, stats in boot_results.items():
    rows[name] = {col: stats[m] for col, m in zip(COL_NAMES, DISPLAY_METRICS)}

table_df = pd.DataFrame(rows).T

formatted_df = table_df.copy()
for col in COL_NAMES:
    formatted_df[col] = formatted_df[col].apply(lambda x: f"{float(x[0]):.3f} ± {float(x[1]):.3f}")

# SAVING FORMATTED BOOTSTRAP TABLE
formatted_df.to_csv(OUTPUT_DIR / "bootstrap_metrics.csv")
print(f"Bootstrap metrics table saved to {OUTPUT_DIR / 'bootstrap_metrics.csv'}")

best_per_col = {
    col: table_df[col].apply(lambda x: x[0]).idxmax()
    for col in COL_NAMES
}


def fmt_cell(mean, std, is_best):
    s = f"{mean:.3f}±{std:.3f}"
    return f"**{s}**" if is_best else s


print(f"{'Model':<28}", "  ".join(f"{c:>16}" for c in COL_NAMES))
print("-" * (28 + 18 * len(COL_NAMES)))
for model_name, row in table_df.iterrows():
    cells = [
        fmt_cell(row[col][0], row[col][1], best_per_col[col] == model_name)
        for col in COL_NAMES
    ]
    print(f"{model_name:<28}", "  ".join(f"{c:>16}" for c in cells))

# ## 9. Interpretability Tools

os.environ["PATH"] += os.pathsep + r"C:\Program Files\Graphviz\bin"


def get_selected_feature_names(model, X):
    selector = model.named_steps["feature_selector"]
    if hasattr(selector, "get_feature_names_out"):
        return list(selector.get_feature_names_out())
    return list(selector.selected_features_)


def transform_with_selector(model, X):
    selector = model.named_steps["feature_selector"]
    feature_names = get_selected_feature_names(model, X)
    X_sel = selector.transform(X)

    if not isinstance(X_sel, pd.DataFrame):
        X_sel = pd.DataFrame(X_sel, columns=feature_names, index=X.index)

    return X_sel, feature_names


logistic_X_train_sel, logistic_features = transform_with_selector(logistic_output["best_model"], X_train)
tree_X_train_sel, tree_features = transform_with_selector(tree_output["best_model"], X_train)

plot_logistic_regression_importance(
    logistic_output["best_model"],
    logistic_features,
    top_n=len(logistic_output["selected_features"]),
)
save_plot("logistic_regression_importance")

get_tree_feature_importance(
    tree_output["best_model"],
    tree_features,
    title="Decision Tree Feature Importance",
)
save_plot("decision_tree_importance")

viz = dtreeviz.model(
    tree_output["best_model"].named_steps["classifier"],
    X_train=tree_X_train_sel,
    y_train=y_train,
    feature_names=tree_features,
    target_name="readmission",
    class_names=["Not Readmitted", "Readmitted"],
)

viz.view(depth_range_to_display=(0, 3)).save(str(OUTPUT_DIR / "dtree_viz.svg"))
print(f"Decision Tree visualization saved to {OUTPUT_DIR / 'dtree_viz.svg'}")

for name in outputs.keys():
    out = outputs[name]
    X_eval_sel, feature_names = transform_with_selector(out["best_model"], X_test)
    shap_values = get_shap(
        out["best_model"],
        X_eval_sel,
        feature_names,
        model_type="linear" if name == "logistic" else "tree",
    )
    out["shap_values"] = shap_values
    out["shap_X_eval"] = X_eval_sel
    out["shap_feature_names"] = feature_names

f2_scorer = make_scorer(fbeta_score, beta=2)
fig, axes = plt.subplots((len(outputs) + 1) // 2, 2, figsize=(18, 14))
axes = axes.flatten()
sns.set_style("white")

if len(outputs) < len(axes):
    axes[-1].axis('off')

for ax, (name, out) in zip(axes, outputs.items()):
    X_eval, feature_names = transform_with_selector(out["best_model"], X_test)
    pfi = permutation_importance(
        out["best_model"], X_eval, y_test,
        scoring=f2_scorer,
        n_repeats=20,
        random_state=42,
        n_jobs=-1,
    )
    pfi_df = pd.DataFrame({
        "feature": feature_names,
        "importance": pfi.importances_mean,
        "std": pfi.importances_std,
    }).sort_values("importance", ascending=False)
    pfi_df = pfi_df[pfi_df["importance"] > 0]
    ax.barh(pfi_df["feature"], pfi_df["importance"],
            xerr=pfi_df["std"], color="steelblue", alpha=0.8)
    ax.axvline(0, color="grey", linestyle="--", linewidth=1)
    ax.set_title(f"PFI — {name}", fontsize=14)
    ax.set_xlabel("Mean decrease in F2", fontsize=12)

plt.suptitle("Permutation Feature Importance", fontsize=18)
plt.tight_layout()
save_plot("permutation_feature_importance")

for name in outputs.keys():
    out = outputs[name]
    X_eval_sel = out["shap_X_eval"]
    feature_names = out["shap_feature_names"]

    y_prob = out["best_model"].predict_proba(X_test)[:, 1]
    high_risk_idx = y_prob.argmax()

    pred_prob = y_prob[high_risk_idx]
    actual_label = "Readmitted" if y_test.iloc[high_risk_idx] == 1 else "Not Readmitted"

    sv_raw = out["shap_values"]
    sv = (
        sv_raw[:, :, 1] if getattr(sv_raw, "ndim", 0) == 3
        else sv_raw[1] if isinstance(sv_raw, list)
        else sv_raw
    )

    plt.figure(figsize=(10, 6))
    shap.waterfall_plot(
        shap.Explanation(
            values=sv[high_risk_idx],
            base_values=sv.mean(axis=0).mean(),
            data=X_eval_sel.iloc[high_risk_idx],
            feature_names=feature_names,
        ),
        show=False,
    )
    plt.title(
        f"Model: {name.upper()} | Risk: {pred_prob:.3f} | Outcome: {actual_label}",
        fontsize=18,
    )
    plt.tight_layout()
    save_plot(f"shap_waterfall_{name}")

model = xgb_output["best_model"].named_steps["classifier"]
importance = model.get_booster().get_score(importance_type="gain")
df_imp = pd.DataFrame(importance.items(), columns=['feature', 'gain'])
df_imp = df_imp.sort_values(by='gain', ascending=False).head(15)

plt.figure(figsize=(10, 6))
sns.set_style("ticks")
sns.barplot(data=df_imp, x='gain', y='feature', palette="magma")
plt.title("XGBoost Clinical Feature Importance (Gain)", fontsize=16, pad=20)
plt.xlabel("Total Gain (Reduction in Loss)", fontsize=12)
plt.ylabel("")
plt.tight_layout()
save_plot("xgboost_gain_importance")

fig, ax = plt.subplots(figsize=(26, 10))
for name, out in outputs.items():
    y_prob = out["best_model"].predict_proba(X_test)[:, 1]
    PrecisionRecallDisplay.from_predictions(y_test, y_prob, name=name, ax=ax)
ax.axhline(y=y_test.mean(), color='grey', linestyle='--', label=f'Baseline ({y_test.mean():.2f})')
ax.set_title("Precision-Recall Curves")
plt.legend()
save_plot("precision_recall_curves")

catboost_model = catboost_output["best_model"]
catboost_clf = catboost_model.named_steps["classifier"]
catboost_feature_names = get_selected_feature_names(catboost_model, X_test)
catboost_importance = catboost_clf.get_feature_importance()

catboost_imp_df = pd.DataFrame({
    "feature": catboost_feature_names,
    "importance": catboost_importance,
}).sort_values("importance", ascending=False).head(15)

plt.figure(figsize=(10, 6))
sns.set_style("ticks")
sns.barplot(data=catboost_imp_df, x="importance", y="feature", palette="magma")

plt.title("CatBoost Clinical Feature Importance", fontsize=16, pad=20)
plt.xlabel("Feature Importance", fontsize=12)
plt.ylabel("")
plt.tight_layout()
save_plot("catboost_feature_importance")

# ## 10. Consensus Analysis

TOP_N = 10

available_shap_models = [
    name for name, out in outputs.items()
    if "shap_values" in out and "shap_feature_names" in out
]

top_shap_per_model = {}
shap_signs_per_model = {}

for name in available_shap_models:
    out = outputs[name]
    sv_raw = out["shap_values"]
    feature_names = out["shap_feature_names"]

    sv = (
        sv_raw[:, :, 1] if getattr(sv_raw, "ndim", 0) == 3
        else sv_raw[1] if isinstance(sv_raw, list)
        else sv_raw
    )

    df_shap = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_shap": np.abs(sv).mean(axis=0),
        "mean_shap": sv.mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)

    top_shap_per_model[name] = df_shap.head(TOP_N)["feature"].tolist()
    shap_signs_per_model[name] = dict(zip(df_shap["feature"], df_shap["mean_shap"]))

f2_scorer = make_scorer(fbeta_score, beta=2)
top_pfi_per_model = {}

for name, out in outputs.items():
    pfi = permutation_importance(
        out["best_model"],
        X_test,
        y_test,
        scoring=f2_scorer,
        n_repeats=20,
        random_state=42,
        n_jobs=-1,
    )

    pfi_df = pd.DataFrame({
        "feature": X_test.columns,
        "importance": pfi.importances_mean,
    }).sort_values("importance", ascending=False)

    top_pfi_per_model[name] = pfi_df[pfi_df["importance"] > 0].head(TOP_N)["feature"].tolist()

tree_clf = tree_output["best_model"].named_steps["classifier"]
tree_feature_names = get_selected_feature_names(tree_output["best_model"], X_test)
tree_used_mask = tree_clf.tree_.feature >= 0
tree_used_indices = sorted(set(tree_clf.tree_.feature[tree_used_mask]))
top_tree = [tree_feature_names[i] for i in tree_used_indices]

top_lr = logistic_output.get("selected_features", top_shap_per_model.get("logistic", []))

xgb_model = xgb_output["best_model"]
xgb_clf = xgb_model.named_steps["classifier"]
xgb_feature_names = get_selected_feature_names(xgb_model, X_test)
xgb_gain_raw = xgb_clf.get_booster().get_score(importance_type="gain")

mapped_gain = []
for feat_key, gain_val in xgb_gain_raw.items():
    if feat_key.startswith("f") and feat_key[1:].isdigit():
        idx = int(feat_key[1:])
        if idx < len(xgb_feature_names):
            mapped_name = xgb_feature_names[idx]
        else:
            mapped_name = feat_key
    else:
        mapped_name = feat_key
    mapped_gain.append((mapped_name, gain_val))

xgb_gain_df = pd.DataFrame(mapped_gain, columns=["feature", "gain"]).sort_values("gain", ascending=False)
top_xgb_gain = xgb_gain_df.head(TOP_N)["feature"].tolist()

cat_model = catboost_output["best_model"]
cat_clf = cat_model.named_steps["classifier"]
cat_feature_names = get_selected_feature_names(cat_model, X_test)
cat_importance = cat_clf.get_feature_importance()

cat_imp_df = pd.DataFrame({
    "feature": cat_feature_names,
    "importance": cat_importance
}).sort_values("importance", ascending=False)

top_catboost_native = cat_imp_df.head(TOP_N)["feature"].tolist()

feature_universe = sorted(
    set(X_test.columns)
    | set(top_tree)
    | set(top_lr)
    | set(top_xgb_gain)
    | set(top_catboost_native)
    | {feat for feats in top_shap_per_model.values() for feat in feats}
    | {feat for feats in top_pfi_per_model.values() for feat in feats}
)

consensus = pd.DataFrame({"feature": feature_universe})

consensus["shap_votes"] = 0
for name in available_shap_models:
    consensus["shap_votes"] += consensus["feature"].isin(top_shap_per_model.get(name, [])).astype(int)

consensus["pfi_votes"] = 0
for name in outputs.keys():
    consensus["pfi_votes"] += consensus["feature"].isin(top_pfi_per_model.get(name, [])).astype(int)

consensus["in_lr"] = consensus["feature"].isin(top_lr).astype(int)
consensus["in_tree"] = consensus["feature"].isin(top_tree).astype(int)
consensus["in_xgb_gain"] = consensus["feature"].isin(top_xgb_gain).astype(int)
consensus["in_catboost"] = consensus["feature"].isin(top_catboost_native).astype(int)

consensus["votes"] = (
        consensus["shap_votes"]
        + consensus["pfi_votes"]
        + consensus["in_lr"]
        + consensus["in_tree"]
        + consensus["in_xgb_gain"]
        + consensus["in_catboost"]
)

consensus = consensus.sort_values(
    ["votes", "shap_votes", "pfi_votes", "feature"],
    ascending=[False, False, False, True]
).reset_index(drop=True)

group_i = consensus[consensus["votes"] >= 12]
group_ii = consensus[(consensus["votes"] >= 10) & (consensus["votes"] <= 11)]
group_iii = consensus[(consensus["votes"] >= 8) & (consensus["votes"] <= 9)]
group_low = consensus[consensus["votes"] <= 7]

plot_df = consensus[consensus["votes"] >= 1].copy()

heatmap_data = plot_df.set_index("feature")[
    ["shap_votes", "pfi_votes", "in_lr", "in_tree", "in_xgb_gain", "in_catboost"]
].rename(columns={
    "shap_votes": "SHAP\nVotes",
    "pfi_votes": "PFI\nVotes",
    "in_lr": "LR\nCoeff",
    "in_tree": "Decision\nTree",
    "in_xgb_gain": "XGB\nGain",
    "in_catboost": "CatBoost\nNative",
})

display_data = heatmap_data.copy().astype(float)

if len(available_shap_models) > 0:
    display_data["SHAP\nVotes"] = display_data["SHAP\nVotes"] / len(available_shap_models)
else:
    display_data["SHAP\nVotes"] = 0.0

display_data["PFI\nVotes"] = display_data["PFI\nVotes"] / len(outputs)
display_data["LR\nCoeff"] = display_data["LR\nCoeff"].astype(float)
display_data["Decision\nTree"] = display_data["Decision\nTree"].astype(float)
display_data["XGB\nGain"] = display_data["XGB\nGain"].astype(float)
display_data["CatBoost\nNative"] = display_data["CatBoost\nNative"].astype(float)

row_colors = []
for v in plot_df["votes"]:
    if v >= 12:
        row_colors.append("#2ecc71")
    elif v >= 10:
        row_colors.append("#f39c12")
    elif v >= 8:
        row_colors.append("#95a5a6")
    else:
        row_colors.append("#ecf0f1")

fig, ax = plt.subplots(figsize=(14, max(5, len(plot_df) * 0.50)))
ax.imshow(display_data.values, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

ax.set_xticks(range(len(display_data.columns)))
ax.set_xticklabels(display_data.columns, fontsize=10)
ax.set_yticks(range(len(plot_df)))
ax.set_yticklabels(plot_df["feature"].tolist(), fontsize=10)

for i in range(len(plot_df)):
    for j, col in enumerate(heatmap_data.columns):
        raw_val = heatmap_data.iloc[i, j]
        color_val = display_data.iloc[i, j]

        if col in ["SHAP\nVotes", "PFI\nVotes"]:
            mark = str(int(raw_val))
        else:
            mark = r"$\checkmark$" if raw_val == 1 else r"$\times$"

        text_color = "white" if color_val > 0 else "#ffcccc"
        ax.text(
            j, i, mark,
            ha="center", va="center",
            fontsize=14, fontweight="bold", color=text_color
        )

for i, color in enumerate(row_colors):
    ax.add_patch(
        plt.Rectangle((-0.5, i - 0.5), 0.15, 1, color=color, clip_on=False)
    )

legend_handles = [
    mpatches.Patch(color="#2ecc71", label="Group I — 12-14 tools (Near Unanimous)"),
    mpatches.Patch(color="#f39c12", label="Group II — 10-11 tools (Strong Consensus)"),
    mpatches.Patch(color="#95a5a6", label="Group III — 8-9 tools (Majority Consensus)"),
    mpatches.Patch(color="#ecf0f1", label="Group IV — ≤7 tools (Model-Specific | Weak predictors)"),
]

ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.20),
    ncol=4,
    fontsize=10,
)

ax.set_title(
    f"Consensus Analysis — Compact Feature Agreement Across Interpretability Tools\nTop {TOP_N} Features Per Tool",
    fontsize=18,
    pad=12,
)

plt.tight_layout()
save_plot("consensus_analysis")
