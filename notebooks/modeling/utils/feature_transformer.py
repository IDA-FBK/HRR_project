from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import chi2
from scipy.stats import mannwhitneyu
import pandas as pd
import numpy as np


class ClinicalFeatureSelector(BaseEstimator, TransformerMixin):
    """
    Feature selector that applies Chi-squared for binary/categorical features
    and Mann-Whitney U for continuous features, selecting those that pass
    their respective test at the specified significance level.
    """

    def __init__(self, alpha=0.05, binary_cols=None):
        """
        Parameters
        ----------
        alpha : float
            Significance threshold for both tests (default: 0.05)
        binary_cols : list or None
            Column names to treat as binary/categorical (Chi2).
            All remaining columns are treated as continuous (MWU).
            If None, inferred automatically from unique value counts.
        """
        self.alpha = alpha
        self.binary_cols = binary_cols
        self.selected_features_ = []
        self.selection_df = pd.DataFrame()

    def fit(self, X, y):
        X = pd.DataFrame(X).copy()
        y = np.asarray(y)

        # Infer binary columns if not provided
        if self.binary_cols is not None:
            binary_cols = [c for c in self.binary_cols if c in X.columns]
        else:
            binary_cols = [
                c for c in X.columns
                if X[c].dropna().nunique() <= 2
            ]

        continuous_cols = [c for c in X.columns if c not in binary_cols]

        rows = []

        # Chi2 for binary/categorical features
        if binary_cols:
            _, chi2_pvals = chi2(X[binary_cols], y)
            for col, p in zip(binary_cols, chi2_pvals):
                rows.append({
                    "feature":  col,
                    "type":     "binary",
                    "test":     "Chi2",
                    "p_value":  p,
                    "selected": p < self.alpha,
                })

        # MWU for continuous features
        for col in continuous_cols:
            pos = X.loc[y == 1, col]
            neg = X.loc[y == 0, col]
            _, p = mannwhitneyu(pos, neg, alternative="two-sided")
            rows.append({
                "feature":  col,
                "type":     "continuous",
                "test":     "MWU",
                "p_value":  p,
                "selected": p < self.alpha,
            })

        self.selection_df = (
            pd.DataFrame(rows)
            .sort_values("p_value")
            .reset_index(drop=True)
        )

        self.selected_features_ = (
            self.selection_df
            .loc[self.selection_df["selected"], "feature"]
            .tolist()
        )

        self._print_summary()
        return self

    def transform(self, X):
        X = pd.DataFrame(X).copy()
        return X[self.selected_features_]

    def get_feature_names_out(self, input_features=None):
        return np.array(self.selected_features_, dtype=object)

    def _print_summary(self):
        total    = len(self.selection_df)
        selected = len(self.selected_features_)
        dropped  = total - selected

        print(f"Feature selection summary (alpha={self.alpha})")
        print(f"  Total:    {total}")
        print(f"  Selected: {selected}")
        print(f"  Dropped:  {dropped}\n")

        print(f"{'Feature':<35} {'Type':<12} {'Test':<6} {'p-value':<12} {'Selected'}")
        print("-" * 75)
        for _, row in self.selection_df.iterrows():
            mark = "yes" if row["selected"] else "no"
            print(
                f"  {row['feature']:<33} {row['type']:<12} "
                f"{row['test']:<6} {row['p_value']:<12.4e} {mark}"
            )