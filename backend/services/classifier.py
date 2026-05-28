import joblib
import json
from catboost import CatBoostClassifier
import pandas as pd
import numpy as np
from features import classification_features
from config import CLASSIFIER_PATH, PREPROCESSOR_PATH_CLASSIFIER, CLASS_NAMES
from utils.python_types import to_python_types

SKILL_FEATURE_LABELS = {
    "python": "Python",
    "java": "Java",
    "c_cpp": "C/C++",
    "sql": "SQL",
    "machine_learning": "Machine Learning",
    "data_analysis": "Data Analysis",
    "cloud_computing": "Cloud",
    "cybersecurity": "Cybersecurity",
    "web_development": "Web Development",
    "devops": "DevOps",
    "networking": "Networking",
    "communication": "Communication",
    "leadership": "Leadership",
    "problem_solving": "Problem Solving",
    "teamwork": "Teamwork",
    "adaptability": "Adaptability",
}

DERIVED_SKILL_FEATURES = {
    "ds_score": ["python", "sql", "machine_learning", "data_analysis"],
    "da_score": ["sql", "data_analysis", "communication"],
    "da_score_v2": ["python", "sql", "machine_learning", "data_analysis", "communication", "devops", "cloud_computing"],
    "ba_score": ["communication", "leadership", "problem_solving", "data_analysis", "python", "machine_learning", "devops"],
    "mle_score": ["python", "machine_learning", "cloud_computing", "devops"],
    "de_score": ["python", "sql", "cloud_computing", "devops", "networking", "machine_learning", "data_analysis"],
    "se_score": ["python", "java", "c_cpp", "web_development", "data_analysis", "machine_learning"],
    "ce_score": ["cloud_computing", "devops", "networking", "cybersecurity", "data_analysis", "machine_learning"],
    "is_data_engineer": ["sql", "cloud_computing", "devops"],
    "is_data_analyst": ["sql", "data_analysis", "machine_learning"],
    "is_software_dev": ["web_development", "java", "data_analysis"],
    "is_cloud_expert": ["cloud_computing", "devops"],
    "is_heavy_ml": ["machine_learning", "python"],
    "is_data_expert": ["sql", "data_analysis"],
    "dev_vs_data": ["web_development", "java", "c_cpp", "data_analysis", "sql"],
    "ml_vs_dev": ["machine_learning", "web_development", "java"],
    "analytics_no_infra": ["data_analysis", "sql", "devops", "cloud_computing"],
    "infra_no_analytics": ["devops", "cloud_computing", "networking", "data_analysis"],
    "da_vs_ds": ["data_analysis", "machine_learning"],
}

class ClassifierService:
    def __init__(self):
        '''Load the pre-trained classifier model and its associated preprocessor from disk.'''
        self.model = joblib.load(CLASSIFIER_PATH)
        self.preprocessor = joblib.load(PREPROCESSOR_PATH_CLASSIFIER) 

    def _prepare_features(self, profile: dict) -> tuple[pd.DataFrame, list[str]]:
        X = pd.DataFrame([profile])
        X = classification_features(X)
        X_processed = self.preprocessor.transform(X)
        feature_names = self.preprocessor.get_feature_names_out()
        X_df = pd.DataFrame(X_processed, columns=feature_names)
        return X_df, list(feature_names)

    def get_scores(self, profile: dict) -> dict:
        '''Given a student's profile, preprocess the data, run it through the classifier model, and return a dictionary of profession probabilities sorted in descending order.'''
        X_df, _ = self._prepare_features(profile)
        probs = self.model.predict_proba(X_df)[0]

        return to_python_types(dict(sorted(
            zip(CLASS_NAMES, probs.tolist()),
            key=lambda x: x[1],
            reverse=True
        )))

    def get_skill_explanations(
        self,
        profile: dict,
        student_skills: list[str] | None = None,
        professions: list[str] | None = None,
        top_n: int = 8,
    ) -> dict:
        """Return local skill-level explanations for classifier probabilities.

        CatBoost can compute local SHAP values directly. If the loaded estimator or
        runtime cannot produce SHAP values, this falls back to a model-aware
        feature-importance/counterfactual estimate: each skill is toggled and the
        resulting probability delta is weighted by feature importance when available.
        """
        professions = professions or CLASS_NAMES
        try:
            shap_result = self._get_catboost_shap_explanations(profile, professions, top_n)
            if shap_result:
                return to_python_types(shap_result)
        except Exception:
            pass

        fallback = self._get_feature_importance_fallback(profile, professions, top_n)
        return to_python_types(fallback)

    def _get_class_index(self, profession: str) -> int | None:
        classes = getattr(self.model, "classes_", None)
        if classes is not None:
            for idx, label in enumerate(classes):
                if str(label) == profession:
                    return idx
        try:
            return CLASS_NAMES.index(profession)
        except ValueError:
            return None

    def _get_catboost_shap_explanations(self, profile: dict, professions: list[str], top_n: int) -> dict:
        if not hasattr(self.model, "get_feature_importance"):
            return {}

        X_df, feature_names = self._prepare_features(profile)
        try:
            from catboost import Pool

            shap_values = self.model.get_feature_importance(
                Pool(X_df),
                type="ShapValues",
            )
        except Exception:
            shap_values = self.model.get_feature_importance(
                X_df,
                type="ShapValues",
            )

        shap_values = np.asarray(shap_values, dtype=float)
        if shap_values.ndim == 3:
            class_values = shap_values[0, :, :-1]
        elif shap_values.ndim == 2 and len(professions) == 2:
            class_values = np.vstack([-shap_values[0, :-1], shap_values[0, :-1]])
        else:
            return {}

        explanations = {}
        for profession in professions:
            class_idx = self._get_class_index(profession)
            if class_idx is None or class_idx >= len(class_values):
                continue
            contributions = self._aggregate_skill_values(class_values[class_idx], feature_names)
            if not any(abs(value) > 1e-9 for value in contributions.values()):
                continue
            explanations[profession] = self._format_skill_explanation(
                profession=profession,
                profile=profile,
                contributions=contributions,
                method="catboost_shap",
                top_n=top_n,
            )
        return explanations

    def _get_feature_importance_fallback(self, profile: dict, professions: list[str], top_n: int) -> dict:
        base_probs = self.get_scores(profile)
        importance_weights = self._skill_importance_weights()
        explanations = {}

        for profession in professions:
            base = float(base_probs.get(profession, 0) or 0)
            contributions = {}
            for skill in SKILL_FEATURE_LABELS:
                if skill not in profile:
                    continue
                toggled = dict(profile)
                current = profile.get(skill, 0)
                if skill in {"communication", "leadership", "problem_solving", "teamwork", "adaptability"}:
                    toggled[skill] = 1 if float(current or 0) > 1 else 5
                else:
                    toggled[skill] = 0 if int(current or 0) else 1
                try:
                    changed = float(self.get_scores(toggled).get(profession, 0) or 0)
                except Exception:
                    changed = base
                contribution = base - changed
                contributions[skill] = contribution * importance_weights.get(skill, 1.0)

            explanations[profession] = self._format_skill_explanation(
                profession=profession,
                profile=profile,
                contributions=contributions,
                method="feature_importance_fallback",
                top_n=top_n,
            )
        return explanations

    def _skill_importance_weights(self) -> dict[str, float]:
        try:
            X_dummy, feature_names = self._prepare_features({
                "field_of_study": "Computer Science",
                "gpa": 3.0,
                **{skill: 0 for skill in SKILL_FEATURE_LABELS},
                "communication": 3,
                "leadership": 3,
                "problem_solving": 3,
                "teamwork": 3,
                "adaptability": 3,
            })
            if hasattr(self.model, "get_feature_importance"):
                raw = np.asarray(self.model.get_feature_importance(), dtype=float)
            else:
                raw = np.asarray(getattr(self.model, "feature_importances_", []), dtype=float)
            if raw.size != len(feature_names) or raw.size == 0:
                return {}
            grouped = self._aggregate_skill_values(raw, feature_names, absolute=True)
            max_value = max(grouped.values()) if grouped else 0
            if max_value <= 0:
                return {}
            return {skill: 0.45 + 0.55 * (value / max_value) for skill, value in grouped.items()}
        except Exception:
            return {}

    def _aggregate_skill_values(
        self,
        values: np.ndarray,
        feature_names: list[str],
        absolute: bool = False,
    ) -> dict[str, float]:
        grouped = {skill: 0.0 for skill in SKILL_FEATURE_LABELS}
        for feature_name, raw_value in zip(feature_names, values):
            value = abs(float(raw_value)) if absolute else float(raw_value)
            clean_name = feature_name.split("__")[-1]
            if clean_name in grouped:
                grouped[clean_name] += value
                continue
            for derived, skills in DERIVED_SKILL_FEATURES.items():
                if clean_name == derived:
                    share = value / max(len(skills), 1)
                    for skill in skills:
                        if skill in grouped:
                            grouped[skill] += share
                    break
        return grouped

    def _format_skill_explanation(
        self,
        profession: str,
        profile: dict,
        contributions: dict[str, float],
        method: str,
        top_n: int,
    ) -> dict:
        ordered = sorted(
            contributions.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:top_n]
        items = []
        for skill, value in ordered:
            present = self._skill_is_present(profile, skill)
            magnitude = self._impact_magnitude(value)
            if value >= 0:
                direction = "positive"
                text = f"{SKILL_FEATURE_LABELS[skill]} {magnitude} increased confidence in {profession}."
            else:
                direction = "negative" if present else "missing"
                text = f"{SKILL_FEATURE_LABELS[skill]} {'gap' if not present else 'signal'} reduced confidence in {profession}."
            items.append(
                {
                    "skill": SKILL_FEATURE_LABELS[skill],
                    "feature": skill,
                    "value": round(float(value), 6),
                    "abs_value": round(abs(float(value)), 6),
                    "direction": direction,
                    "present": present,
                    "magnitude": magnitude,
                    "text": text,
                }
            )

        positive = [item for item in items if item["value"] > 0]
        negative = [item for item in items if item["value"] < 0]
        lead_positive = ", ".join(item["skill"] for item in positive[:3]) or "your strongest current skills"
        lead_negative = ", ".join(item["skill"] for item in negative[:3]) or "no major missing skill"
        return {
            "profession": profession,
            "method": method,
            "items": items,
            "positive": positive[:5],
            "negative": negative[:5],
            "summary": (
                f"For {profession}, {lead_positive} supported the recommendation. "
                f"{lead_negative} is the main area that lowered the model confidence or still looks like a gap."
            ),
        }

    def _skill_is_present(self, profile: dict, skill: str) -> bool:
        value = profile.get(skill, 0)
        if skill in {"communication", "leadership", "problem_solving", "teamwork", "adaptability"}:
            return float(value or 0) >= 3
        return bool(int(value or 0))

    def _impact_magnitude(self, value: float) -> str:
        value = abs(float(value))
        if value >= 0.08:
            return "strongly"
        if value >= 0.025:
            return "moderately"
        return "slightly"
