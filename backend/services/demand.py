import joblib
import json
import pandas as pd
import numpy as np
from datetime import datetime
from config import VACANCY_DATA_PATH, MODELS_DIR, PREPROCESSOR_PATH_DEMAND
from features import demand_features
from lightgbm import LGBMRegressor

class DemandService:
    def __init__(self):
        self.df = pd.read_csv(VACANCY_DATA_PATH)
        self.df['job_posted_date'] = pd.to_datetime(self.df['job_posted_date'])
        
        with open(MODELS_DIR / 'lasso_features.json', 'r') as f:
            self.features = json.load(f)
        with open(MODELS_DIR / 'demand_model_params.json', 'r') as f:
            self.model_params = json.load(f)
            
        self.preprocessor = joblib.load(PREPROCESSOR_PATH_DEMAND)
        self.model = LGBMRegressor(**self.model_params, verbose=-1)
        
        print("Pre-computing demand scores for the current week. Please wait...")
        pred_date = self._get_prediction_date()
        self._cached_scores = self._compute_scores(pred_date)
        print("Demand scores cached successfully!")

    def _get_prediction_date(self) -> pd.Timestamp:
        today = datetime.today()
        date_2023 = today.replace(year=2023)
        return pd.Timestamp(date_2023).to_period('W').to_timestamp('W')

    def get_scores(self) -> dict:
        return self._cached_scores

    def _compute_scores(self, pred_date) -> dict:
        df_train = self.df[self.df['job_posted_date'] <= pred_date].copy()
        
        df_features = demand_features(df_train)
        df_features = df_features.dropna()
        X_train = df_features.drop(columns=['vacancy_count'])
        X_train_processed = self.preprocessor.transform(X_train)
        y_train = df_features['vacancy_count']

        self.model.fit(X_train_processed[self.features], y_train)

        last_rows = (
            df_features
            .sort_values('job_posted_date')
            .groupby('job_title_unified')
            .tail(1)
        )

        X = last_rows
        X_processed = self.preprocessor.transform(X)

        professions = last_rows['job_title_unified'].values
        preds = self.model.predict(X_processed[self.features])

        pred_df = pd.DataFrame({
            'profession': professions,
            'predicted': np.maximum(preds, 0)
        })

        max_vacancies = (
            self.df.groupby('job_title_unified')['vacancy_count']
            .max()
            .to_dict()
        )

        total_pred = pred_df['predicted'].sum() or 1

        scores = {}
        for _, row in pred_df.iterrows():
            prof = row['profession']
            pred = row['predicted']
            max_val = max_vacancies.get(prof, 1)

            scores[prof] = {
                'trend_score':         float(round(pred / max_val, 3)),
                'market_share':        float(round(pred / total_pred, 3)),
                'predicted_vacancies': int(round(pred))
            }

        return dict(sorted(
            scores.items(),
            key=lambda x: x[1]['trend_score'],
            reverse=True
        ))
