# CareerFlow Profile Classifier

This research module supports the deployed CareerFlow MVP and originated in the graduation project. The serving classifier uses field of study, GPA, technical indicators, soft-skill ratings and derived features to produce profile-fit signals for career ranking. Training labels come from synthetic profile data; they do not represent observed career success.

The classifier is one signal in the application's weighted ranking, alongside skill similarity and historical demand; its classification metrics do not evaluate the complete recommendation system.

---

## Dataset provenance and preparation

Source: hafsaatm’s [Career Path Recommendation](https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation) on Kaggle. The upstream description explicitly calls this synthetic educational/research data. Its education/background fields, technical skills, soft skills and three recommended-job labels correspond to `data/raw/career_multilabel_dataset.csv` (2,000 rows). The current training pipeline uses `recommended_job_1` as its target; it does not train a top-three multi-label serving model.

`notebooks/data_preparation.ipynb` maps and filters profession labels, then calls `src/synt_balancing.py::balance_dataset` with the seven supported classes and `target_count=300`. That helper generates rows for underrepresented classes, including absent Data Analyst and Data Engineer classes, using local profession-specific rules. The derived file is `data/balanced/career_multilabel_dataset_balanced.csv`. This step is part of training reproducibility, not evidence of observed career outcomes. Serving features exclude age and gender even though those columns exist in the raw dataset.

License check on 2026-10-07: the [Kaggle metadata endpoint](https://www.kaggle.com/api/v1/datasets/view/hafsaatm/career-path-recommendation) reports `licenseName: "Unknown"`. No explicit dataset reuse license was verified. The original import revision/checksum was not recorded. See the root [data provenance table](../../README.md#data-and-reviewer-workflow) for the separate job-market source.

---

## Project Pipeline (Methodology)

The entire development process of the machine learning model is divided into sequential stages, each recorded in a separate Jupyter notebook:

1. **Data Preparation (`data_preparation.ipynb`):** Missing value handling, duplicate removal, and type conversion to ensure format consistency.
2. **Exploratory Data Analysis (`eda.ipynb`):** Analyzing feature distributions, identifying correlations, and examining target variable imbalance.
3. **Feature Engineering (`feature_engineering.ipynb`):** Generating new informative features (such as scores for each specialty and contrast metrics to differentiate overlapping professions).
4. **Feature Selection (`feature_selection.ipynb`):** Identifying the most significant predictors (using Feature Importance and SHAP) to reduce dimensionality and prevent overfitting. The selected features are saved in `configs/tree_features.json`.
5. **Modeling and Tuning (`modeling.ipynb`):** Training baseline and ensemble models. This stage primarily focuses on hyperparameter optimization using **Optuna** and maximizing a custom metric (Target Scorer) optimized for the F1-score of minority classes (specifically, the 4th class).

---

## Repository Structure

```text
ml/classification/
├── configs/            # JSON configurations (e.g., selected features)
├── data/               # Checked-in synthetic source and derived datasets
│   ├── raw/            # Initial dataset
│   ├── not_processed/  # Intermediate data
│   ├── processed/      # Prepared dataset for ML
│   └── balanced/       # Dataset after rule-based synthetic balancing
├── notebooks/          # Core research Jupyter notebooks
├── results/            # Final metrics (classification_report.csv) and training logs
├── src/                # Supporting Python modules
│   ├── report.py       # Custom report generation (classification_report_custom)
│   └── synt_balancing.py # Rule-based synthetic profile balancing
├── pyproject.toml      # Project configuration and metadata
└── uv.lock             # uv lockfile for exact dependency reproduction
```
---

## Modeling Results

One of the main challenges of this dataset is the severe class imbalance. Baseline models like Logistic Regression and Random Forest showed a performance drop on rare professions (specifically, class 3 / "4th class").

To mitigate this problem, weighted loss functions (class_weight, auto_class_weights='Balanced') and gradient boosting algorithms optimized with Bayesian search were applied.

### Saved Test-Set Experiments

Values below come from [classification_report_fixed.csv](results/classification_report_fixed.csv), whose per-class columns use profession names. Each row refers to one recorded experiment; metrics are not combined across variants. For the two `XGBoost (preprocessed)` rows in the CSV, the table uses the higher-accuracy row.

`selected features` refers to feature-selection experiments; `processed`/`preprocessed` refers to preprocessing such as StandardScaler and OneHotEncoder. The notebook's `4th class` tuning scorer uses `labels=[3]`, targeting Data Engineer, rather than macro F1 over all professions.

| Recorded model | Accuracy | Macro F1 | Weighted F1 | Data Engineer F1 |
| :--- | ---: | ---: | ---: | ---: |
| **CatBoost (processed dataset)** | **0.8440** | **0.8094** | **0.8413** | 0.6250 |
| LightGBM (4th class) | 0.8245 | 0.7840 | 0.8208 | 0.5932 |
| XGBoost (preprocessed) | 0.8404 | 0.8054 | 0.8368 | 0.6207 |
| Random Forest | 0.8050 | 0.7518 | 0.7904 | 0.4421 |
| Logistic Regression | 0.8191 | 0.7811 | 0.8164 | 0.6549 |

These are saved research results on synthetic labels, not newly reproduced benchmarks, probabilities of career success or validation on real student outcomes. Other variants and all per-class metrics remain in the CSV.

---

## Installation and Usage

1. **Clone the repository and navigate to this research module:**
   ```bash
   git clone https://github.com/danialyermekov/careerflow.git
   cd careerflow/ml/classification
   ```

2. **Synchronize the project environment:**
   The project uses *uv* for package management, which reads the pyproject.toml and *uv.lock* files to set up the exact development environment.
   ```bash
   uv sync --locked
   ```

3. **Select the research interpreter:**
   This module's [pyproject.toml](pyproject.toml) requires Python **>=3.14**, independently of the backend's Python 3.11–3.13 requirement. Use this module's `.venv` as the kernel in your notebook editor; `uv` reuses an existing environment. A Jupyter notebook editor/kernel must be available separately; it is not declared in this module's dependencies.

4. **Run the research notebooks:**
   Run the notebooks in the `notebooks/` directory sequentially, starting with `data_preparation.ipynb`, using `notebooks/` as the working directory because paths are relative to it. Ensure the required derived datasets exist before running `modeling.ipynb`. Notebook execution can regenerate datasets and append experiment reports; the metrics above describe the checked-in results rather than a guaranteed fresh run.
