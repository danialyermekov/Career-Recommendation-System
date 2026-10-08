from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Literal, Annotated
from uuid import UUID

class StudentProfile(BaseModel):
    # For roadmap and skill matcher
    skills: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(max_length=200)
    
    # For classifier
    field_of_study: str = Field(min_length=1, max_length=120)
    gpa: float = Field(ge=2, le=4)
    python: int = Field(ge=0, le=1)
    java: int = Field(ge=0, le=1)
    c_cpp: int = Field(ge=0, le=1)
    sql: int = Field(ge=0, le=1)
    machine_learning: int = Field(ge=0, le=1)
    data_analysis: int = Field(ge=0, le=1)
    cloud_computing: int = Field(ge=0, le=1)
    cybersecurity: int = Field(ge=0, le=1)
    web_development: int = Field(ge=0, le=1)
    devops: int = Field(ge=0, le=1)
    networking: int = Field(ge=0, le=1)
    communication: int = Field(ge=0, le=5)
    leadership: int = Field(ge=0, le=5)
    problem_solving: int = Field(ge=0, le=5)
    teamwork: int = Field(ge=0, le=5)
    adaptability: int = Field(ge=0, le=5)
    lang: Literal['en', 'ru', 'kk'] = 'en'

class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(max_length=16000)

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    history: list[ChatMessage] = Field(max_length=40)
    message: str = Field(min_length=1, max_length=8000)
    deep: bool = False
    lang: Literal['en', 'ru', 'kk'] = 'en'


class TrialMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=1000)


class TrialRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=1000)
    history: list[TrialMessage] = Field(default_factory=list, max_length=4)
    lang: Literal['en', 'ru', 'kk'] = 'en'
    consent: Literal[True]

    @model_validator(mode='after')
    def meaningful_message(self):
        self.message = self.message.strip()
        if not self.message:
            raise ValueError('A question is required.')
        return self


class RoadmapProgressRequest(BaseModel):
    doneSkills: list[str] = []
    categoryOrder: list[str] = []
    skillOrders: dict[str, list[str]] = {}
    selectedProfession: Optional[str] = None


class CourseFilterPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filters: dict = {}

class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['review', 'feature', 'bug']
    title: Optional[str] = Field(default=None, max_length=120)
    rating: Optional[int] = Field(default=None, ge=1, le=5, strict=True)
    message: str = Field(default='', max_length=2000)
    reproduction_steps: str = Field(default='', max_length=2000)
    public_consent: bool = Field(default=False, strict=True)
    session_id: Optional[UUID] = None
    website: str = Field(default='', max_length=200)

    @model_validator(mode='after')
    def meaningful_feedback(self):
        self.message = self.message.strip()
        self.title = self.title.strip() if self.title else None
        self.reproduction_steps = self.reproduction_steps.strip()
        if self.type == 'review':
            if self.rating is None or self.title or self.reproduction_steps:
                raise ValueError('A review requires a rating and accepts an optional comment.')
        elif self.type == 'feature':
            if not self.title or len(self.title) < 5 or len(self.message) < 10 or self.rating is not None or self.reproduction_steps:
                raise ValueError('A feature needs a title of 5–120 characters and description of 10–2000 characters.')
        elif not self.title or not self.message or self.rating is not None:
            raise ValueError('A bug report needs a title and description.')
        return self

class FeedbackVoteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    voted: bool = Field(strict=True)
