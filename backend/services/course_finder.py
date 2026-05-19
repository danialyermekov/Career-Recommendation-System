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
        diff_map = {0: 'Beginner', 1: 'Intermediate', 2: 'Advanced'}
    
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

        df['fair_score'] = df['rating'] * (1+ np.log1p(1+df['number_of_reviews']))


        df = df.sort_values(
            by=['match_level', 'fair_score'],
            ascending=[True, False]
        )

        df = df.drop_duplicates(subset=['title'], keep='first')
        df['difficulty_label'] = df['difficulty'].map(diff_map)
        df['difficulty_label'] = df['difficulty_label'].replace({pd.NA: None, float('nan'): None})
        results = []
        for _, row in df.head(top_n).iterrows():
            results.append({
                'title': safe(row['title']),
                'description': safe(row['description']),
                'platform': safe(row['platform']),
                'rating': round(safe(row['rating']), 2),
                'reviews': int(safe(row['number_of_reviews'])),
                'difficulty': safe(row.get('difficulty_label')),
                'certificate': safe(row.get('certificate')),
                'course_url': safe(row.get('course_url'))
            })

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

            df['fair_score'] = df['rating'] * (1+ np.log1p(1+df['number_of_reviews']))

            df = df.sort_values(by=['match_level', 'fair_score'], ascending=[True, False])
            df = df.drop_duplicates(subset=['title'], keep='first')

            for _, row in df.iterrows():
                if len(results) >= top_n:
                    break
                if row['title'] not in used_titles:
                    results.append({
                        'title':       safe(row['title']),
                        'description': safe(row['description']),
                        'platform':    safe(row['platform']),
                        'rating':      round(float(row['rating'] or 0), 2),
                        'reviews':     int(row['number_of_reviews'] or 0),
                        'course_url':  safe(row.get('course_url')),
                        'difficulty':  safe(row.get('difficulty')),
                        'certificate': safe(row.get('certificate')),
                    })
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
                        'courses': self._find_courses_en(skill) if lang == 'en' else self._find_courses_ru(skill)
                    }

            return result, roadmap['full'] 
