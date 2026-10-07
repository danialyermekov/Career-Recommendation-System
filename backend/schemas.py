from pydantic import BaseModel
from typing import Optional

class StudentProfile(BaseModel):
    # For roadmap and skill matcher
    skills: list[str]
    
    # For classifier
    field_of_study: str
    gpa: float
    python: int
    java: int
    c_cpp: int
    sql: int
    machine_learning: int
    data_analysis: int
    cloud_computing: int
    cybersecurity: int
    web_development: int
    devops: int
    networking: int
    communication: int
    leadership: int
    problem_solving: int
    teamwork: int
    adaptability: int
    lang: str = 'en' 

class ChatMessage(BaseModel):
    role: str      # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    session_id: str
    history: list[ChatMessage]
    message: str
    deep: bool = False
    lang: str = 'en'


class RoadmapProgressRequest(BaseModel):
    doneSkills: list[str] = []
    categoryOrder: list[str] = []
    skillOrders: dict[str, list[str]] = {}
    selectedProfession: Optional[str] = None


class CourseFilterPreferencesRequest(BaseModel):
    filters: dict = {}
    user_id: str = 'demo'
