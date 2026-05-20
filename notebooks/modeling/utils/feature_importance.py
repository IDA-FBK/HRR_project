import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_logistic_regression_importance(
    model,
    feature_names,
    top_n=20,
    title='Logistic Regression Feature Importance',
    annotate=True,
):
    # Extract coefficients
    # classifier is the step name for models
    coeffs = model.named_steps['classifier'].coef_[0]

    # Build the DataFrame
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'coefficient': coeffs
    })

    # Process for sorting
    feature_importance['abs_coefficient'] = feature_importance['coefficient'].abs()
    feature_importance = feature_importance.sort_values('abs_coefficient', ascending=False)

    # Filter and re-sort for visualization
    top_features = feature_importance.head(top_n).copy()
    top_features = top_features.sort_values('coefficient', ascending=True)

    # Visualization
    fig_height = max(5, 0.45 * len(top_features))
    plt.figure(figsize=(12, fig_height))
    colors = ['#c0392b' if c > 0 else '#2980b9' for c in top_features['coefficient']]

    bars = plt.barh(
        top_features['feature'],
        top_features['coefficient'],
        color=colors,
        edgecolor='black',
        alpha=0.85
    )

    plt.axvline(x=0, color='grey', linestyle='--', linewidth=1.2)
    plt.title(title, fontsize=15)
    plt.xlabel('Coefficient', fontsize=12)
    plt.ylabel('Feature', fontsize=12)
    plt.tight_layout()

    # Add data labels only when the plot is not too crowded
    if annotate and len(top_features) <= 15:
        x_span = max(top_features['abs_coefficient'].max(), 1e-6)
        offset = 0.02 * x_span
        for bar in bars:
            width = bar.get_width()
            ha_alignment = 'left' if width > 0 else 'right'
            x_text = width + offset if width > 0 else width - offset
            plt.text(
                x_text,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.3f}',
                ha=ha_alignment,
                va='center',
                fontsize=10
            )

    plt.show()

    return top_features
# For tree-based models, we can directly use the feature_importances_ attribute to get the importance scores for each feature. This method is efficient and provides a clear indication of which features are most influential in the model's predictions.
def get_tree_feature_importance(
    model,
    feature_names,
    top_n=20,
    normalize=True,
    title='Tree Feature Importance'
):
    # Extract the classifier from the pipeline
    clf = model.named_steps['classifier']

    # Build Importance DataFrame
    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': clf.feature_importances_
    })

    # Filter out features with 0 importance (not used in any split)
    importance_df = importance_df[importance_df['Importance'] > 0].copy()

    if normalize and not importance_df.empty:
        importance_df['Importance'] = importance_df['Importance'] / importance_df['Importance'].sum()

    importance_df = importance_df.sort_values('Importance', ascending=False).head(top_n)

    # Create Visualization
    fig_height = max(5, 0.45 * len(importance_df))
    plt.figure(figsize=(12, fig_height))
    sns.barplot(
        x='Importance',
        y='Feature',
        data=importance_df.sort_values('Importance', ascending=False),
        palette='magma'
    )

    plt.title(title, fontsize=15)
    plt.xlabel('Normalized Tree Importance' if normalize else 'Tree Importance', fontsize=12)
    plt.ylabel('Feature', fontsize=12)
    plt.tight_layout()
    plt.show()

    # Return only the features that actually contributed to the model
    return importance_df