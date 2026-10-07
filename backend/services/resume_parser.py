from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillRule:
    label: str
    patterns: tuple[str, ...]


SKILL_RULES: tuple[SkillRule, ...] = (
    SkillRule("Python", (r"\bpython\b",)),
    SkillRule("JavaScript", (r"\bjavascript\b", r"\bjs\b")),
    SkillRule("TypeScript", (r"\btypescript\b", r"\bts\b")),
    SkillRule("Java", (r"\bjava\b",)),
    SkillRule("C++", (r"\bc\+\+\b", r"\bcpp\b")),
    SkillRule("C#", (r"\bc#\b", r"\bcsharp\b")),
    SkillRule("Go", (r"\bgolang\b", r"\bgo\s+(developer|engineer|language|programming)\b")),
    SkillRule("R", (r"\br\s+(programming|language)\b", r"\brstudio\b", r"\btidyverse\b", r"\bggplot2\b", r"\bdplyr\b")),
    SkillRule("SQL", (r"\bsql\b",)),
    SkillRule("PostgreSQL", (r"\bpostgresql\b", r"\bpostgres\b")),
    SkillRule("MySQL", (r"\bmysql\b",)),
    SkillRule("MongoDB", (r"\bmongodb\b", r"\bmongo\b")),
    SkillRule("Redis", (r"\bredis\b",)),
    SkillRule("Machine Learning", (r"\bmachine\s+learning\b", r"\bml\b")),
    SkillRule("Deep Learning", (r"\bdeep\s+learning\b",)),
    SkillRule("Data Analysis", (r"\bdata\s+analysis\b", r"\banalytics\b")),
    SkillRule("Pandas", (r"\bpandas\b",)),
    SkillRule("NumPy", (r"\bnumpy\b",)),
    SkillRule("scikit-learn", (r"\bscikit[-\s]?learn\b", r"\bsklearn\b")),
    SkillRule("TensorFlow", (r"\btensorflow\b",)),
    SkillRule("PyTorch", (r"\bpytorch\b",)),
    SkillRule("Keras", (r"\bkeras\b",)),
    SkillRule("React", (r"\breact(?:\.js|js)?\b",)),
    SkillRule("Vue", (r"\bvue(?:\.js|js)?\b",)),
    SkillRule("Angular", (r"\bangular\b",)),
    SkillRule("Node.js", (r"\bnode(?:\.js|js)?\b",)),
    SkillRule("FastAPI", (r"\bfastapi\b",)),
    SkillRule("Django", (r"\bdjango\b",)),
    SkillRule("Flask", (r"\bflask\b",)),
    SkillRule("Docker", (r"\bdocker\b",)),
    SkillRule("Kubernetes", (r"\bkubernetes\b", r"\bk8s\b")),
    SkillRule("Terraform", (r"\bterraform\b",)),
    SkillRule("AWS", (r"\baws\b", r"\bamazon\s+web\s+services\b")),
    SkillRule("Azure", (r"\bazure\b",)),
    SkillRule("GCP", (r"\bgcp\b", r"\bgoogle\s+cloud\b")),
    SkillRule("Cloud Computing", (r"\bcloud\s+computing\b", r"\bcloud\s+infrastructure\b")),
    SkillRule("DevOps", (r"\bdevops\b", r"\bci/cd\b", r"\bci\s*cd\b")),
    SkillRule("Git", (r"\bgit\b", r"\bgithub\b", r"\bgitlab\b")),
    SkillRule("Linux", (r"\blinux\b",)),
    SkillRule("Bash", (r"\bbash\b", r"\bshell\s+scripting\b")),
    SkillRule("Networking", (r"\bnetworking\b", r"\btcp/ip\b")),
    SkillRule("Cybersecurity", (r"\bcybersecurity\b", r"\binformation\s+security\b")),
    SkillRule("Tableau", (r"\btableau\b",)),
    SkillRule("Power BI", (r"\bpower\s*bi\b",)),
    SkillRule("Excel", (r"\bexcel\b",)),
    SkillRule("Airflow", (r"\bairflow\b",)),
    SkillRule("Spark", (r"\bspark\b", r"\bpyspark\b")),
    SkillRule("Kafka", (r"\bkafka\b",)),
    SkillRule("Hadoop", (r"\bhadoop\b",)),
    SkillRule("REST", (r"\brest(?:ful)?\b",)),
    SkillRule("GraphQL", (r"\bgraphql\b",)),
    SkillRule("Agile", (r"\bagile\b",)),
    SkillRule("Scrum", (r"\bscrum\b",)),
)

ROLE_RULES: tuple[tuple[str, str], ...] = (
    ("Data Scientist", r"\bdata\s+scientist\b"),
    ("Data Analyst", r"\bdata\s+analyst\b"),
    ("Data Engineer", r"\bdata\s+engineer\b"),
    ("Business Analyst", r"\bbusiness\s+analyst\b"),
    ("Machine Learning Engineer", r"\b(machine\s+learning|ml)\s+engineer\b"),
    ("Software Engineer", r"\bsoftware\s+engineer\b"),
    ("Cloud Engineer", r"\bcloud\s+engineer\b"),
    ("Frontend Developer", r"\bfront[-\s]?end\s+developer\b"),
    ("Backend Developer", r"\bback[-\s]?end\s+developer\b"),
    ("Full Stack Developer", r"\bfull[-\s]?stack\s+developer\b"),
)


def extract_text_from_upload(filename: str, content: bytes) -> str:
    lower_name = filename.lower()
    is_pdf = lower_name.endswith(".pdf") or content[:4] == b"%PDF"

    if is_pdf:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PDF parsing requires pymupdf. Install backend dependencies with `pip install .` or run Docker build.") from exc

        text_parts: list[str] = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text("text"))
        return "\n".join(text_parts)

    for encoding in ("utf-8", "utf-16", "cp1251", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def parse_resume_text(text: str) -> dict:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    lowered = normalized.lower()

    skills: list[str] = []
    for rule in SKILL_RULES:
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in rule.patterns):
            skills.append(rule.label)

    detected_role = ""
    for role, pattern in ROLE_RULES:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            detected_role = role
            break

    return {
        "skills": skills,
        "role": detected_role,
        "text_preview": normalized[:1200],
    }
