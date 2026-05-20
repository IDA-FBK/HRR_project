import shap
import matplotlib.pyplot as plt
import numpy as np

# SHAP utility function to compute and plot SHAP values for a given model and test set, with optional feature filtering based on mean absolute SHAP value
def get_shap(model, X_test,feature_names, model_type='linear', shap_threshold=None, max_display_features=12, min_relative_importance=0.01):
    classifier = model.named_steps['classifier']

    if 'scaler' in model.named_steps:
        X_input = model.named_steps['scaler'].transform(X_test)
    else:
        X_input = X_test.values if hasattr(X_test, 'values') else X_test

    # Use appropriate SHAP explainer based on model type
    if model_type == 'linear':
        explainer = shap.LinearExplainer(classifier, X_input)
    elif model_type == 'tree':
        explainer = shap.TreeExplainer(classifier)
    else:
        explainer = shap.KernelExplainer(classifier.predict_proba, X_input)

    shap_values = explainer.shap_values(X_input)

    if isinstance(shap_values, list):
        plot_values = shap_values[1]
    elif shap_values.ndim == 3:
        plot_values = shap_values[:, :, 1]
    else:
        plot_values = shap_values

    # Filter to features with meaningful SHAP impact
    mean_abs_shap = np.abs(plot_values).mean(axis=0)

    # If a manual threshold is provided, use it directly.
    # Otherwise, compute a visualization cutoff from the top-k features
    # and a small relative floor based on the strongest feature.
    if shap_threshold is not None:
        cutoff = shap_threshold
    else:
        nonzero = mean_abs_shap[mean_abs_shap > 0]

        if len(nonzero) == 0:
            cutoff = np.inf
        else:
            k = min(max_display_features, len(nonzero))
            kth_value = np.partition(nonzero, -k)[-k]
            relative_floor = min_relative_importance * nonzero.max() #
            cutoff = max(kth_value, relative_floor)

    mask = mean_abs_shap >= cutoff

    # Fallback in case the cutoff is too strict for a particular model/output
    if not np.any(mask):
        top_idx = np.argsort(mean_abs_shap)[-min(max_display_features, len(mean_abs_shap)):]
        mask = np.zeros_like(mean_abs_shap, dtype=bool)
        mask[top_idx] = True

    plot_values_filtered = plot_values[:, mask]
    X_input_filtered = X_input[:, mask]
    feature_names_filtered = [f for f, m in zip(feature_names, mask) if m]

    # Print summary and plot SHAP values for the filtered set of features
    n_selected = mask.sum()
    n_total = len(feature_names)
    print(
        f"Showing {n_selected}/{n_total} features "
        f"(cutoff={cutoff:.6f}, max_display_features={max_display_features})"
    )

    plt.figure()
    shap.summary_plot(
        plot_values_filtered,
        X_input_filtered,
        feature_names=feature_names_filtered,
        max_display=n_selected,   # show all selected, no artificial cap
        plot_size=(14, max(6, n_selected * 0.35)),  # dynamic height
        show=False,
    )
    plt.title(f"SHAP Global Explanation: {type(classifier).__name__}", fontsize=16)
    plt.tight_layout()
    plt.show()

    return shap_values  # return full unfiltered values for downstream use
def plot_shap_dependence(shap_values_raw, X_eval_sel, feature_names,
                          feature_of_interest, interaction_feature,
                          title_prefix=''):
    """
    Plots a SHAP dependence plot using precomputed SHAP values.
    
    Parameters:
        shap_values_raw: precomputed SHAP values from out["shap_values"]
        X_eval_sel: transformed test set from out["shap_X_eval"]
        feature_names: list from out["shap_feature_names"]
        feature_of_interest: str, main feature on x-axis
        interaction_feature: str, feature used for coloring
        title_prefix: str, model name for plot title
    """
    # Handle different SHAP value formats
    sv = (
        shap_values_raw[:, :, 1] if getattr(shap_values_raw, "ndim", 0) == 3
        else shap_values_raw[1] if isinstance(shap_values_raw, list)
        else shap_values_raw
    )

    # Validate features exist
    if feature_of_interest not in feature_names:
        print(f"Feature '{feature_of_interest}' not found in feature_names.")
        return
    if interaction_feature not in feature_names:
        print(f"Feature '{interaction_feature}' not found in feature_names.")
        return

    foi_idx = feature_names.index(feature_of_interest)
    int_idx = feature_names.index(interaction_feature)

    # Convert to numpy if DataFrame
    X_input = X_eval_sel.values if hasattr(X_eval_sel, 'values') else X_eval_sel

    plt.figure(figsize=(10, 6))
    shap.dependence_plot(
        foi_idx,
        sv,
        X_input,
        feature_names=feature_names,
        interaction_index=int_idx,
        show=False
    )
    plt.title(
        f"{title_prefix} — SHAP Dependence: {feature_of_interest} × {interaction_feature}",
        fontsize=13
    )
    plt.tight_layout()
    plt.show()