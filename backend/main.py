import time
import json
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from schemas import StudentProfile, ChatRequest
from services.classifier import ClassifierService
from services.demand import DemandService
from services.skill_matcher import SkillMatcherService
from services.course_finder import CourseFinderService
from services.llm import LLMService
from top_profession import get_top_profession
from roadmap import generate_roadmap

class SessionStore:
    def __init__(self, ttl_seconds: int = 86400):
        self.store = {}
        self.ttl = ttl_seconds

    def set(self, session_id: str, context: str):
        self.store[session_id] = (context, time.time() + self.ttl)

    def get(self, session_id: str) -> str:
        now = time.time()

        expired = [k for k, (v, exp) in self.store.items() if now > exp]
        for k in expired:
            del self.store[k]
            
        data = self.store.get(session_id)
        return data[0] if data and data[1] > now else "No context available."

sessions = SessionStore()
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading ML models and services into memory...")
    ml_models['classifier'] = ClassifierService()
    ml_models['demand'] = DemandService()
    ml_models['skill_matcher'] = SkillMatcherService()
    ml_models['course_finder'] = CourseFinderService()
    ml_models['llm'] = LLMService()
    print("All models loaded successfully.")
    
    yield
    
    print("Shutting down server, clearing model memory...")
    ml_models.clear()

app = FastAPI(title='IT Career Advisor API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], 
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/recommend')
def recommend(profile: StudentProfile):
    try:
        skill_scores = ml_models['skill_matcher'].get_scores(profile.skills)

        profile_dict = profile.dict(exclude={'skills'})
        classification_scores = ml_models['classifier'].get_scores(profile_dict)

        demand_scores = ml_models['demand'].get_scores()

        top_profession, final_scores, top_2 = get_top_profession(
            classification_scores=classification_scores,
            demand_scores=demand_scores,
            skill_scores=skill_scores
        )

        roadmap_with_courses, full_roadmap = ml_models['course_finder'].get_roadmap_with_courses(
            profession=top_profession,
            student_skills=profile.skills,
            lang=profile.lang,
        )

        context = ml_models['llm'].build_context(
            skills=profile.skills,
            skill_scores=skill_scores,
            classification_scores=classification_scores,
            demand_scores=demand_scores,
            roadmap_with_courses=roadmap_with_courses,
        )
        
        session_id = str(uuid4())
        sessions.set(session_id, context)

        return {
            'top_profession':        top_profession,
            'session_id':            session_id,
            'alternative_profession': top_2[1],  
            'final_scores':          final_scores,
            'skill_scores':          skill_scores,
            'classification_scores': classification_scores,
            'demand_scores':         demand_scores,
            'roadmap_with_courses':  roadmap_with_courses,
            'full_roadmap':          full_roadmap,
            'context':               context,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/chat')
def chat(request: ChatRequest):
    context = sessions.get(request.session_id)
    try:
        response = ml_models['llm'].chat(
            context=context,
            history=request.history,
            message=request.message,
        )
        return {'response': response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/chat/stream')
def chat_stream(request: ChatRequest):
    context = sessions.get(request.session_id)

    def generate():
        try:
            for chunk in ml_models['llm'].chat_stream(
                context=context,
                history=request.history,
                message=request.message,
                deep=request.deep
            ):
                yield chunk
                
        except Exception as e:
            error_data = {"type": "text", "content": f"Streaming error: {str(e)}"}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",  
        }
    )
