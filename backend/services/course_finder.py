import pandas as pd
import numpy as np
import re
from roadmap import generate_roadmap
from config import COURSES_PATH, ROADMAP_PATH, TOP_N_COURSES
import json
from utils.python_types import safe

class CourseFinderService:
    def __init__(self):
        self.courses = pd.read_csv(COURSES_PATH)
        with open(ROADMAP_PATH, 'r') as f:
            self.profession_profiles = json.load(f)

    def _normalize_level(self, raw) -> str:
        text = str(safe(raw) or '').strip().lower()
        if text in {'0', '0.0'} or 'beginner' in text or 'нач' in text:
            return 'Beginner'
        if text in {'1', '1.0'} or 'intermediate' in text or 'сред' in text:
            return 'Intermediate'
        if text in {'2', '2.0'} or 'advanced' in text or 'продвин' in text or 'профессион' in text:
            return 'Advanced'
        if 'mixed' in text or 'all' in text or 'все' in text or 'любой' in text:
            return 'Mixed'
        return 'Mixed'

    def _normalize_certificate(self, raw) -> bool:
        text = str(safe(raw) or '').strip().lower()
        return text in {'true', '1', 'yes', 'y', 'да', 'certificate', 'сертификат'}

    def _detect_language(self, row) -> str:
        if 'language' in row and safe(row.get('language')):
            text = str(row.get('language')).strip().lower()
            if text.startswith('en'):
                return 'en'
            if text.startswith('ru'):
                return 'ru'
            if text.startswith('kk') or text.startswith('kz'):
                return 'kk'
            return 'other'

        text = f"{safe(row.get('title')) or ''} {safe(row.get('description')) or ''}"
        if re.search(r'[ӘәҒғҚқҢңӨөҰұҮүҺһІі]', text):
            return 'kk'
        if re.search(r'[А-Яа-яЁё]', text):
            return 'ru'
        if re.search(r'[A-Za-z]', text):
            return 'en'
        return 'other'

    def _infer_price_type(self, row) -> str:
        for col in ('price_type', 'price', 'is_paid', 'is_free'):
            if col not in row or pd.isna(row.get(col)):
                continue
            numeric = pd.to_numeric(row.get(col), errors='coerce')
            if pd.notna(numeric):
                if col == 'is_paid':
                    return 'paid' if float(numeric) > 0 else 'free'
                if col == 'is_free':
                    return 'free' if float(numeric) > 0 else 'paid'
                return 'free' if float(numeric) <= 0 else 'paid'
            text = str(row.get(col)).strip().lower()
            if text in {'free', '0', '0.0', 'false', 'no', 'бесплатно', 'тегін'}:
                return 'free'
            if text in {'paid', 'true', 'yes', 'платно', 'ақылы'}:
                return 'paid'
        platform = str(safe(row.get('platform')) or '').strip().lower()
        if platform in {'udemy', 'udacity'}:
            return 'paid'
        if platform in {'stepik', 'coursera', 'edx'}:
            return 'free'
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
        price_type = self._infer_price_type(row)
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
            'price_type': price_type,
            'price': self._normalize_price_amount(row),
        }

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

    def _find_courses_for_locale(self, skill: str, lang: str) -> list:
        if lang == 'en':
            primary = self._find_courses_en(skill)
            secondary = self._find_courses_ru(skill)
        else:
            primary = self._find_courses_ru(skill)
            secondary = self._find_courses_en(skill)
        return self._merge_course_lists(primary, secondary, limit=TOP_N_COURSES * 2)

    def _find_courses_en(
        self,
        skill: str,
        top_n: int = TOP_N_COURSES
    ) -> list:
        '''Find courses related to a specific skill, ranked by relevance and quality.
        Relevance is determined by:
        1. Whether the skill appears in the title (especially in the first 40 characters).
        2. Whether the skill appears in the description.
        Quality is determined by a "fair score" that combines rating and number of reviews.'''
        
        skill_clean = skill.lower().replace('_', ' ')
        df = self.courses.copy()
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)
        df['number_of_reviews'] = pd.to_numeric(df['number_of_reviews'], errors='coerce').fillna(0)
        
        df['_title_lower'] = df['title'].str.lower()
        df['_desc_lower'] = df['description'].astype(str).str.lower()
        
        safe_skill = re.escape(skill_clean)

        pattern = rf'(?<!\w){safe_skill}(?!\w)'

        mask_in_title = df['_title_lower'].str.contains(pattern, regex=True, na=False)
        mask_in_desc = df['_desc_lower'].str.contains(pattern, regex=True, na=False)
        
        combined_mask = mask_in_title | mask_in_desc
        df = df[combined_mask].copy()
        
        if df.empty:
            return []

        mask_in_title = mask_in_title[combined_mask]
        mask_in_desc = mask_in_desc[combined_mask]

        mask_level_1 = df['_title_lower'].str[:40].str.contains(skill_clean, regex=False, na=False)
        mask_level_2 = mask_in_title & ~mask_level_1
        mask_level_3 = mask_in_desc & ~mask_in_title

        conditions = [mask_level_1, mask_level_2, mask_level_3]
        df['match_level'] = np.select(conditions, [1, 2, 3], default=4)

        df['fair_score'] = df['rating'] * np.log1p(df['number_of_reviews'])


        df = df.sort_values(
            by=['match_level', 'fair_score'],
            ascending=[True, False]
        )

        df = df.drop_duplicates(subset=['title'], keep='first')
        results = []
        for _, row in df.head(top_n).iterrows():
            results.append(self._serialize_course_row(row))

        return results


    def _find_courses_ru(self,
    skill: str,
    top_n: int = TOP_N_COURSES
    ) -> list:
        '''Find courses related to a specific skill, prioritizing Russian language courses and relevance of the skill in the title, then by rating and number of reviews.'''

        skill_clean = skill.lower().replace('_', ' ')
        results = []
        used_titles = set()

        self.courses['rating'] = pd.to_numeric(self.courses['rating'], errors='coerce').fillna(0)
        self.courses['number_of_reviews'] = pd.to_numeric(self.courses['number_of_reviews'], errors='coerce').fillna(0)

        priorities = sorted(p for p in self.courses['priority'].unique() if pd.notna(p))

        for priority in priorities:
            if len(results) >= top_n:
                break

            platform_df = self.courses[self.courses['priority'] == priority].copy()

            title_lower = platform_df['title'].str.lower()
            desc_lower  = platform_df['description'].astype(str).str.lower()

            mask_title_front = title_lower.str[:40].str.contains(skill_clean, regex=False, na=False)
            mask_title_any   = title_lower.str.contains(skill_clean, regex=False, na=False)
            mask_desc        = desc_lower.str.contains(skill_clean, regex=False, na=False)

            combined_mask = mask_title_any | mask_desc
            df = platform_df[combined_mask].copy()

            if df.empty:
                continue

            df['match_level'] = np.select(
                [mask_title_front[combined_mask], mask_title_any[combined_mask] & ~mask_title_front[combined_mask], mask_desc[combined_mask] & ~mask_title_any[combined_mask]],
                [1, 2, 3],
                default=4
            )

            df['fair_score'] = df['rating'] * np.log1p(df['number_of_reviews'])

            df = df.sort_values(by=['match_level', 'fair_score'], ascending=[True, False])
            df = df.drop_duplicates(subset=['title'], keep='first')

            for _, row in df.iterrows():
                if len(results) >= top_n:
                    break
                if row['title'] not in used_titles:
                    results.append(self._serialize_course_row(row))
                    used_titles.add(row['title'])

        return results
    
    def get_roadmap_with_courses(
            self,
            profession: str,
            student_skills: list[str],
            lang: str = 'en'
        ) -> dict:
            '''Generate a personalized roadmap for a given profession and student skills, and find relevant courses for each skill gap.'''
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
                        'courses': self._find_courses_for_locale(skill, lang)
                    }

            return result, roadmap['full']

    def get_gap_summary_for_all(self, student_skills: list[str]) -> dict:
        """Return full/gap roadmap summaries for every profession without course lookup."""
        summaries = {}
        for profession, profession_profile in self.profession_profiles.items():
            roadmap = generate_roadmap(
                profession=profession,
                student_raw_skills=student_skills,
                profession_profile=profession_profile,
            )
            summaries[profession] = {
                'full': roadmap.get('full', {}),
                'gap': roadmap.get('gap', {}),
            }
        return summaries
