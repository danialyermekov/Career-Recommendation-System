import pandas as pd
import numpy as np
import re
import json
import threading
from typing import Any
from roadmap import generate_roadmap
from config import COURSES_PATH, ROADMAP_PATH, TOP_N_COURSES
from utils.python_types import safe

class CourseFinderService:
    def __init__(self):
        self.courses = pd.read_csv(COURSES_PATH)
        with open(ROADMAP_PATH, 'r') as f:
            self.profession_profiles = json.load(f)
        # Thread-safe in-memory cache for course matching
        self._cache_lock = threading.Lock()
        self._course_cache = {}
        # Precompute the prepared dataframe once at startup
        self._df_prepared = self._prepare_base_dataframe()

    def _normalize_level(self, raw) -> str:
        text = str(safe(raw) or '').strip().lower()
        if text in {'0', '0.0'} or 'beginner' in text or 'нач' in text:
            return 'Beginner'
        if text in {'1', '1.0'} or 'intermediate' in text or 'сред' in text:
            return 'Intermediate'
        if text in {'2', '2.0'} or 'advanced' in text or 'продвин' in text or 'профессион' in text:
            return 'Advanced'
        return 'Mixed'

    def _normalize_certificate(self, raw) -> bool:
        text = str(safe(raw) or '').strip().lower()
        return text in {'true', '1', 'yes', 'y', 'да', 'certificate', 'сертификат'}

    def _detect_language(self, row) -> str:
        if 'language' in row and safe(row.get('language')):
            text = str(row.get('language')).strip().lower()
            if text.startswith('en'): return 'en'
            if text.startswith('ru'): return 'ru'
            if text.startswith('kk') or text.startswith('kz'): return 'kk'
            return 'other'

        text = f"{safe(row.get('title')) or ''} {safe(row.get('description')) or ''}"
        if re.search(r'[ӘәҒғҚқҢңӨөҰұҮүҺһІі]', text): return 'kk'
        if re.search(r'[А-Яа-яЁё]', text): return 'ru'
        if re.search(r'[A-Za-z]', text): return 'en'
        return 'other'

    def _infer_price_type(self, row) -> str:
        for col in ('price_type', 'price', 'is_paid', 'is_free'):
            if col not in row or pd.isna(row.get(col)):
                continue
            numeric = pd.to_numeric(row.get(col), errors='coerce')
            if pd.notna(numeric):
                if col == 'is_paid': return 'paid' if float(numeric) > 0 else 'free'
                if col == 'is_free': return 'free' if float(numeric) > 0 else 'paid'
                return 'free' if float(numeric) <= 0 else 'paid'
            text = str(row.get(col)).strip().lower()
            if text in {'free', '0', '0.0', 'false', 'no', 'бесплатно', 'тегін'}: return 'free'
            if text in {'paid', 'true', 'yes', 'платно', 'ақылы'}: return 'paid'
        
        platform = str(safe(row.get('platform')) or '').strip().lower()
        if platform in {'udemy', 'udacity'}: return 'paid'
        if platform in {'stepik', 'coursera', 'edx'}: return 'free'
        return 'unknown'

    def _normalize_price_amount(self, row):
        if 'price' not in row or pd.isna(row.get('price')):
            return None
        numeric = pd.to_numeric(row.get('price'), errors='coerce')
        if pd.isna(numeric):
            return None
        return round(float(numeric), 2)

    def _serialize_course_row(self, row) -> dict:
        level = self._normalize_level(row.get('difficulty'))
        return {
            'title': safe(row['title']),
            'description': safe(row['description']),
            'platform': safe(row['platform']),
            'rating': round(float(safe(row.get('rating')) or 0), 2),
            'reviews': int(safe(row.get('number_of_reviews')) or 0),
            'difficulty': level,
            'level': level,
            'certificate': self._normalize_certificate(row.get('certificate')),
            'course_url': safe(row.get('course_url')),
            'language': self._detect_language(row),
            'price_type': self._infer_price_type(row),
            'price': self._normalize_price_amount(row),
        }

    def _apply_dynamic_filters(self, df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
        """Применяет кастомные пользовательские фильтры к DataFrame перед ранжированием."""
        if not filters:
            return df

        # Фильтр по уровню сложности (передается списком или строкой, например: ['Beginner', 'Intermediate'])
        if 'levels' in filters and filters['levels']:
            target_levels = [l.lower() for l in filters['levels']]
            df = df[df['_level_normalized'].str.lower().isin(target_levels)]

        # Фильтр по типу цены ('free', 'paid')
        if 'price_types' in filters and filters['price_types']:
            target_prices = [p.lower() for p in filters['price_types']]
            df = df[df['_price_type_inferred'].str.lower().isin(target_prices)]

        # Фильтр по платформам (например: ['stepik', 'coursera'])
        if 'platforms' in filters and filters['platforms']:
            target_platforms = [p.lower() for p in filters['platforms']]
            df = df[df['platform'].astype(str).str.lower().isin(target_platforms)]

        # Фильтр по языкам (например: ['ru', 'en'])
        if 'languages' in filters and filters['languages']:
            df = df[df['_lang_detected'].isin(filters['languages'])]

        # Наличие сертификата (bool)
        if 'has_certificate' in filters and filters['has_certificate'] is not None:
            df = df[df['_cert_normalized'] == bool(filters['has_certificate'])]

        # Дополнительный текстовый текстовый поиск внутри результатов (подстрока)
        if 'search_query' in filters and filters['search_query']:
            q = str(filters['search_query']).lower().strip()
            df = df[df['_title_lower'].str.contains(q, regex=False, na=False) | 
                    df['_desc_lower'].str.contains(q, regex=False, na=False)]

        return df

    def _merge_course_lists(self, *course_lists: list, limit: int | None = None) -> list:
        merged = []
        seen = set()
        for courses in course_lists:
            for course in courses or []:
                key = (
                    str(course.get('title') or '').strip().lower(),
                    str(course.get('platform') or '').strip().lower(),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(course)
                if limit and len(merged) >= limit:
                    return merged
        return merged

    def _find_courses_for_locale(self, skill: str, lang: str, filters: dict[str, Any] | None = None) -> list:
        # Convert filters dict to a hashable type for robust cache lookup
        filters_key = None
        if filters:
            def make_hashable(val):
                if isinstance(val, list):
                    return tuple(make_hashable(item) for item in val)
                if isinstance(val, dict):
                    return frozenset((k, make_hashable(v)) for k, v in val.items())
                return val
            filters_key = frozenset((k, make_hashable(v)) for k, v in filters.items() if v is not None)
            
        cache_key = (skill, lang, filters_key)
        
        with self._cache_lock:
            if cache_key in self._course_cache:
                return self._course_cache[cache_key]

        if lang == 'en':
            primary = self._find_courses_en(skill, filters=filters)
            secondary = self._find_courses_ru(skill, filters=filters)
        else:
            primary = self._find_courses_ru(skill, filters=filters)
            secondary = self._find_courses_en(skill, filters=filters)
            
        result = self._merge_course_lists(primary, secondary, limit=TOP_N_COURSES)
        
        with self._cache_lock:
            self._course_cache[cache_key] = result
            
        return result

    def _prepare_base_dataframe(self) -> pd.DataFrame:
        """Предварительно вычисляет базовые признаки для фильтрации и ранжирования."""
        if not hasattr(self, '_df_prepared') or self._df_prepared is None:
            if not hasattr(self, 'courses') or self.courses is None:
                return pd.DataFrame()
            df = self.courses.copy()
            # Downcast ratings and review counts to minimize memory footprint and speed up calculations
            df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0).astype(np.float32)
            df['number_of_reviews'] = pd.to_numeric(df['number_of_reviews'], errors='coerce').fillna(0).astype(np.int32)
            df['_title_lower'] = df['title'].str.lower()
            df['_desc_lower'] = df['description'].astype(str).str.lower()
            
            # Ленивая нормализация для применения фильтров на уровне векторных операций
            df['_level_normalized'] = df['difficulty'].apply(self._normalize_level).astype('category')
            df['_price_type_inferred'] = df.apply(self._infer_price_type, axis=1).astype('category')
            df['_lang_detected'] = df.apply(self._detect_language, axis=1).astype('category')
            df['_cert_normalized'] = df['certificate'].apply(self._normalize_certificate)
            
            if 'priority' in df.columns:
                df['priority'] = pd.to_numeric(df['priority'], errors='coerce')
            
            if 'platform' in df.columns:
                df['platform'] = df['platform'].astype('category')
                
            self._df_prepared = df
        return self._df_prepared

    def _find_courses_en(self, skill: str, top_n: int = TOP_N_COURSES, filters: dict[str, Any] | None = None) -> list:
        skill_clean = skill.lower().replace('_', ' ')
        df = self._prepare_base_dataframe()
        
        safe_skill = re.escape(skill_clean)
        pattern = rf'(?<!\w){safe_skill}(?!\w)'

        mask_in_title = df['_title_lower'].str.contains(pattern, regex=True, na=False)
        mask_in_desc = df['_desc_lower'].str.contains(pattern, regex=True, na=False)
        
        combined_mask = mask_in_title | mask_in_desc
        df = df[combined_mask].copy()
        
        # Применение динамических фильтров пользователя
        df = self._apply_dynamic_filters(df, filters or {})

        if df.empty:
            return []

        # Пересчет масок под отфильтрованный датафрейм
        mask_level_1 = df['_title_lower'].str[:40].str.contains(skill_clean, regex=False, na=False)
        mask_level_2 = df['_title_lower'].str.contains(pattern, regex=True, na=False) & ~mask_level_1
        mask_level_3 = df['_desc_lower'].str.contains(pattern, regex=True, na=False) & ~df['_title_lower'].str.contains(pattern, regex=True, na=False)

        conditions = [mask_level_1, mask_level_2, mask_level_3]
        df['match_level'] = np.select(conditions, [1, 2, 3], default=4)
        df['fair_score'] = df['rating'] * np.log1p(df['number_of_reviews'])

        df = df.sort_values(by=['match_level', 'fair_score'], ascending=[True, False])
        df = df.drop_duplicates(subset=['title'], keep='first')
        
        return [self._serialize_course_row(row) for _, row in df.head(top_n).iterrows()]

    def _find_courses_ru(self, skill: str, top_n: int = TOP_N_COURSES, filters: dict[str, Any] | None = None) -> list:
        skill_clean = skill.lower().replace('_', ' ')
        base_df = self._prepare_base_dataframe()
        
        # Filter out rows where priority is NaN to match original loop logic exactly
        base_df_valid = base_df[base_df['priority'].notna()]
        
        # Search title and description for matching terms
        title_lower = base_df_valid['_title_lower']
        desc_lower  = base_df_valid['_desc_lower']

        mask_title_any   = title_lower.str.contains(skill_clean, regex=False, na=False)
        mask_desc        = desc_lower.str.contains(skill_clean, regex=False, na=False)

        combined_mask = mask_title_any | mask_desc
        df = base_df_valid[combined_mask].copy()
        
        # Применение динамических фильтров пользователя
        df = self._apply_dynamic_filters(df, filters or {})

        if df.empty:
            return []

        # Vectorized match level calculation
        title_sub_lower = df['_title_lower'].str[:40]
        mask_level_1 = title_sub_lower.str.contains(skill_clean, regex=False, na=False)
        mask_level_2 = df['_title_lower'].str.contains(skill_clean, regex=False, na=False) & ~mask_level_1
        mask_level_3 = df['_desc_lower'].str.contains(skill_clean, regex=False, na=False) & ~df['_title_lower'].str.contains(skill_clean, regex=False, na=False)

        conditions = [mask_level_1, mask_level_2, mask_level_3]
        df['match_level'] = np.select(conditions, [1, 2, 3], default=4)
        df['fair_score'] = df['rating'] * np.log1p(df['number_of_reviews'])

        # Multi-column sort by priority ascending, match_level ascending, and fair_score descending
        df = df.sort_values(by=['priority', 'match_level', 'fair_score'], ascending=[True, True, False])
        df = df.drop_duplicates(subset=['title'], keep='first')

        results = []
        for _, row in df.head(top_n).iterrows():
            results.append(self._serialize_course_row(row))
        return results

    def get_roadmap_with_courses(
        self,
        profession: str,
        student_skills: list[str],
        lang: str = 'en',
        filters: dict[str, Any] | None = None
    ) -> tuple[dict, list]:
        """Генерация базовой карты (вызывается один раз при инициализации)."""
        profession_profile = self.profession_profiles.get(profession, {})

        roadmap = generate_roadmap(
            profession=profession,
            student_raw_skills=student_skills,
            profession_profile=profession_profile,
        )

        result = {}
        for cat, skills in roadmap['gap'].items():
            result[cat] = {}
            for skill in skills:
                result[cat][skill] = {
                    'courses': self._find_courses_for_locale(skill, lang, filters=filters)
                }

        return result, roadmap['full']

    def update_courses_by_filters(
        self, 
        skills_gaps: list[str], 
        lang: str = 'en', 
        filters: dict[str, Any] | None = None
    ) -> dict[str, list]:
        """Быстрый пересчет только курсов для переданного списка навыков при изменении фильтров.
        
        Принимает плоский список навыков (gaps), требующих обучения.
        """
        updated_courses = {}
        for skill in skills_gaps:
            updated_courses[skill] = self._find_courses_for_locale(skill, lang, filters=filters)
        return updated_courses

    def get_gap_summary_for_all(self, student_skills: list[str], lang: str = 'en') -> dict:
        """Рассчитывает gap и full роадмапы для всех имеющихся профессий."""
        summaries = {}
        for profession in self.profession_profiles.keys():
            profession_profile = self.profession_profiles.get(profession, {})
            roadmap = generate_roadmap(
                profession=profession,
                student_raw_skills=student_skills,
                profession_profile=profession_profile,
            )
            
            # Находим курсы для всех gap-скиллов этой профессии
            roadmap_with_courses = {}
            for cat, skills in roadmap['gap'].items():
                roadmap_with_courses[cat] = {}
                for skill in skills:
                    roadmap_with_courses[cat][skill] = {
                        'courses': self._find_courses_for_locale(skill, lang)
                    }
                    
            summaries[profession] = {
                "full": roadmap["full"],
                "gap": roadmap["gap"],
                "roadmap_with_courses": roadmap_with_courses
            }
        return summaries