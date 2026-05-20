# Hospital Readmission Prediction

A machine learning framework for predicting 30-day hospital readmission from inpatient episode data.

## Overview

This repository contains an end-to-end pipeline for readmission prediction, from cohort construction and feature extraction to grouped model training, evaluation, and interpretability.

The project is designed around three goals:

- reduce data leakage through patient-level splitting and grouped validation
- optimize clinically relevant thresholds with recall-aware model selection
- support transparent interpretation through SHAP, permutation importance, and consensus analysis

## Data Description

The project uses administrative healthcare to predict whether 30-days readmission risk.

### Cohort

The analytical cohort includes patients with selected target conditions:

- Heart Failure
- COPD
- Stroke
- Pneumonia
- Ischaemic Heart Disease

### Data Levels

The repository includes data at multiple levels:

- patient level: used for readmission flags and patient-level splitting
- inpatient episode level: used as the main modeling unit
- healthcare event level: used to summarize prior service utilization, medications, and costs

### Main Feature Groups

The modeling dataset includes variables related to:

- demographics
- comorbidity burden
- disease indicators
- prior inpatient, emergency, and ambulatory utilization
- medication history
- hospitalization characteristics such as length of stay and discharge department

### Descriptive Analysis

Descriptive analysis is developed in [notebooks/data_description.ipynb](notebooks/data_description.ipynb) and supported by [sql/data_description.sql](sql/data_description.sql).

This part of the project summarizes:

- overall readmission rate
- readmission rate by condition
- age distribution
- length-of-stay patterns
- healthcare utilization and cost trends
- department-level and seasonal variation

Summary tables are stored in [data/processed/healthcare_events_part](data/processed/healthcare_events_part), and figures are exported to [plots](plots).

## Workflow

The framework follows a structured pipeline:

1. Define the cohort and create analytical tables using SQL scripts in [sql](sql)
2. Export the source data into tabular format using [source/get_data.py](source/get_data.py)
3. Load processed patient and episode datasets from [data/processed](data/processed)
4. Perform patient-level train/test splitting with [notebooks/modeling/utils/train_test_split.py](notebooks/modeling/utils/train_test_split.py)
5. Apply deterministic preprocessing through [notebooks/modeling/utils/preprocess.py](notebooks/modeling/utils/preprocess.py)
6. Run fold-specific feature selection with [notebooks/modeling/utils/feature_transformer.py](notebooks/modeling/utils/feature_transformer.py)
7. Train and tune models with grouped cross-validation through [notebooks/modeling/utils/model_trainer.py](notebooks/modeling/utils/model_trainer.py)
8. Evaluate, compare, and interpret models in [notebooks/modeling/modeling_pipeline.ipynb](notebooks/modeling/modeling_pipeline.ipynb)

## Modeling Approach

The project evaluates multiple tabular learning methods under the same training and evaluation framework:

- Logistic Regression
- Decision Tree
- Balanced Random Forest
- XGBoost
- CatBoost

The evaluation process includes:

- grouped hyperparameter tuning
- grouped threshold calibration
- refitting on the full training data
- final testing on an untouched patient-level test set

The operating threshold is selected to optimize a configurable metric, typically F2-score, under a minimum recall constraint.

## Evaluation and Interpretability

Performance is assessed with both threshold-based and ranking metrics, including:

- Accuracy
- Precision
- Recall
- F1-score
- F2-score
- ROC-AUC
- PR-AUC

The framework also includes:

- bootstrap summaries on the held-out test set
- logistic coefficient importance
- tree-based feature importance
- SHAP explanations
- permutation feature importance
- consensus analysis across interpretability tools

The main evaluation and interpretation workflow is implemented in [notebooks/modeling/modeling_pipeline.ipynb](notebooks/modeling/modeling_pipeline.ipynb).

## Repository Structure

- [sql](sql): SQL scripts for cohort extraction, feature engineering, labeling, and descriptive analysis
- [source](source): standalone scripts for data extraction and plotting
- [notebooks](notebooks): exploratory, descriptive, and modeling notebooks
- [notebooks/modeling/utils](notebooks/modeling/utils): reusable utilities for splitting, preprocessing, training, metrics, and interpretation
- [data/interim](data/interim): intermediate datasets
- [data/processed](data/processed): processed analytical and modeling datasets
- [data/splits](data/splits): saved train/test episode splits
- [plots](plots): exported figures and visual summaries

## Main Files

Key entry points in the repository include:

- [notebooks/modeling/modeling_pipeline.ipynb](notebooks/modeling/modeling_pipeline.ipynb): main modeling workflow
- [notebooks/data_description.ipynb](notebooks/data_description.ipynb): descriptive analysis
- [notebooks/feature_engineering_selection.ipynb](notebooks/feature_engineering_selection.ipynb): feature engineering and selection exploration
- [source/get_data.py](source/get_data.py): data extraction script
- [notebooks/modeling/utils/model_trainer.py](notebooks/modeling/utils/model_trainer.py): grouped training and threshold calibration logic

## Outputs

The project generates outputs in the following locations:

- [data/processed/modeling](data/processed/modeling): modeling datasets and metric summaries
- [data/processed/healthcare_events_part](data/processed/healthcare_events_part): descriptive summaries
- [data/splits](data/splits): patient-level train/test splits mapped to episodes
- [plots](plots): visual outputs for descriptive and modeling analyses

## Notes

This repository is notebook-driven, with the core reusable framework implemented in [notebooks/modeling/utils](notebooks/modeling/utils). 