# CareerFlow Profile Classifier

This research module is part of the CareerFlow graduation project. The serving classifier uses field of study, GPA, technical indicators, soft-skill ratings and derived features to produce profile-fit signals for career ranking. Training labels come from synthetic profile data; they do not represent observed career success.

The problem addressed by this project is highly relevant to the **HR Tech** industry, career consulting, and educational platforms, helping users build optimal vectors for professional development.

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
predict_career/
├── configs/            # JSON configurations (e.g., selected features)
├── data/               # Data directory (excluded from version control)
│   ├── raw/            # Initial dataset
│   ├── not_processed/  # Intermediate data
│   ├── processed/      # Prepared dataset for ML
│   └── balanced/       # Datasets after oversampling/undersampling
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

### Summary Metric Table (Best Models on the Test Set)

selected - selected_features_catboost.json(features after catboost feature selection)
processed - dataset after preprocessor (Standart Scaler, OneHotEncoder)
4-th class - target scorer (f1-macro for 4th class)

| Модель | Accuracy | F1 (Macro) | F1 (4-th class) |
| :--- | :--- | :--- | :--- | :--- |
| **CatBoost (processed)** | **0.8440** | **0.8024** | 0.65 |
| **LightGBM (4th class)** | 0.8422 | 0.8 | **0.8448** |
| **XGBoost (processed)** | 0.8404 | 0.8054 | 0.62 |
| **Random Forest** | 0.8050 | 0.7518 | 0.4421 |
| **Logistic Regression** | 0.8191 | 0.7811 | 0.6549 |

---

## Installation and Usage

1. **Clone the repository and navigate to the project directory:**
   ```bash
   git clone <Repository_URL>
   cd predict_career
   ```

2. **Synchronize the project environment:**
   The project uses *uv* for package management, which reads the pyproject.toml and *uv.lock* files to set up the exact development environment.
   ```bash
   uv sync
   ```

3. **Activate the virtual environment:**
   ```bash
    # For Windows:
    .venv\Scripts\activate
    # For Linux/Mac:
    source .venv/bin/activate
   ```

4. **Run the research notebooks:**
   To verify the pipeline, run the notebooks in the `notebooks/` directory sequentially, starting with `data_preparation.ipynb`. Ensure that all processed datasets are generated before running modeling.ipynb.