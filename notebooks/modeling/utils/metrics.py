import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sklearn.metrics import (fbeta_score, f1_score, recall_score, precision_score, accuracy_score, average_precision_score, roc_auc_score, classification_report, confusion_matrix)
# Helper function to evaluate model performance and print metrics, confusion matrix, and save results to CSV for later comparison
def evaluate_model_performance(y_true, y_pred, y_prob, threshold, model_name, target_recall, features_used):
    # Metrics & Area Under Curves
    f2 = fbeta_score(y_true, y_pred, beta=2)
    f1 = f1_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    accuracy = accuracy_score(y_true, y_pred)
    pr_auc = average_precision_score(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)
    # Print metrics in a nice format
    print(f"\n" + "="*40)
    print(f"EVALUATION: {model_name.upper()}")
    print(f"="*40)
    print(f"Target Recall Constraint:  {target_recall}")
    print(f"Optimal Threshold (CV):    {threshold:.4f}")
    print("-" * 40)
    print(f"Accuracy:                  {accuracy:.3f}")
    print(f"Precision:                 {precision:.3f}")
    print(f"Recall (Sensitivity):      {recall:.3f}")
    print(f"F1-Score:                  {f1:.3f}")
    print(f"F2-Score (Recall-Biased):  {f2:.3f}")
    print(f"AUC-ROC:                   {roc_auc:.3f}")
    print(f"PR-AUC:                    {pr_auc:.3f}")
    print("-" * 40)
    # Create CSV with: model name, metrics, threshold, target recall constraint, features used, etc. for comparison tables later
    results_df = pd.DataFrame([{
        "model_name": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "f2_score": f2,
        "auc_roc": roc_auc,
        "pr_auc": pr_auc,
        "threshold": threshold,
        "target_recall_constraint": target_recall,
        "features_len": len(features_used),
        "features_used": ", ".join(features_used)
        
    }])
    # Append to existing CSV
    file_exists = pd.io.common.file_exists("../../data/processed/modeling/metrics_model_comparison.csv")
    results_df.to_csv("../../data/processed/modeling/metrics_model_comparison.csv", index=False, header=not file_exists, mode="a")
    # Print Confusion Matrix (False Positives, False Negatives, True Positives, True Negatives)
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
    plt.title(f'{model_name} Confusion Matrix\n(Threshold: {threshold:.2f})', fontsize=14)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.ylabel('Actual Label', fontsize=12)
    plt.show()

    # Return dictionary for comparison tables
    return {
        "Model": model_name,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "F2": f2,
        "AUC-ROC": roc_auc,
        "PR-AUC": pr_auc,
        "Len Features": len(features_used),
        "Optimal Threshold": threshold,
        "Features Used": features_used
    }