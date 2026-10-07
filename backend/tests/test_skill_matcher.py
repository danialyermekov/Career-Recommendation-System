import json
import os
from pathlib import Path
import subprocess
import sys


def test_skill_vectors_are_stable_across_process_hash_seeds():
    code = """
import json
from services.skill_matcher import SkillMatcherService
service = SkillMatcherService()
skills = ['Python', 'SQL', 'Pandas', 'Git', 'Excel']
print(json.dumps({'scores': service.get_scores(skills), 'skills': service.get_user_skills_ranked(skills)}))
"""
    outputs = []
    for seed in ("1", "2"):
        process = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.append(json.loads(process.stdout))
    assert outputs[0] == outputs[1]
    assert len(outputs[0]["scores"]) == 7
