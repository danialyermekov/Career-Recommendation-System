from pathlib import Path
from urllib.parse import unquote
from typing import Any
from fastapi import FastAPI, HTTPException, Request, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from schemas import StudentProfile, ChatRequest, RoadmapProgressRequest, CourseFilterPreferencesRequest
import json
from services.llm import LLMError, safe_llm_error, validate_credentials
from top_profession import get_top_profession
from config import CLASSIFIER_COEF, SKILL_MATCHER_COEF, DEMAND_TREND_COEF, DEMAND_MARKET_SHARE_COEF
from uuid import uuid4
from database import (
    DEMO_USER_ID,
    delete_recommendation_history,
    get_recommendation_state,
    init_db,
    list_recommendation_history,
    save_course_filter_preferences,
    save_recommendation_session,
    update_recommendation_progress,
)

session_store: dict[str, str] = {}
FRONTEND_BUILD_DIR = (Path(__file__).resolve().parent.parent / 'frontend' / 'build').resolve()

CAREER_TOPIC_KEYWORDS = {
    "career", "profession", "job", "role", "roadmap", "skill", "skills", "gap", "course",
    "learning", "recommendation", "score", "profile", "market", "demand", "salary",
    "interview", "resume", "cv", "portfolio", "data", "engineer", "analyst", "cloud",
    "software", "machine learning", "ml", "ai",
    "карьера", "профессия", "работа", "роль", "роадмап", "план", "навык", "навыки",
    "пробел", "курс", "обучение", "рекомендация", "оценка", "профиль", "рынок",
    "спрос", "зарплата", "резюме", "собеседование",
    "мансап", "мамандық", "жұмыс", "рөл", "жоспар", "дағды", "дағдылар",
    "курс", "оқу", "ұсыныс", "баға", "нарық", "сұраныс", "түйіндеме",
}

PROMPT_INJECTION_PATTERNS = {
    "ignore previous", "ignore all previous", "system prompt", "developer message",
    "internal instruction", "reveal instructions", "jailbreak", "dan mode",
    "забудь инструкции", "игнорируй инструкции", "системный промпт",
    "внутренние инструкции", "раскрой инструкции",
}

OFF_TOPIC_PATTERNS = {
    "bubble sort", "quick sort", "write code", "generate code", "solve math",
    "math problem", "essay", "poem", "lyrics", "recipe", "weather",
    "пузырьковую сортировку", "напиши код", "сгенерируй эссе",
    "реши задачу", "математик", "стих", "рецепт", "погода",
    "код жаз", "эссе жаз", "математика", "есеп шығар",
}

OFF_TOPIC_RESPONSES = {
    "ru": "Я могу консультировать только по карьерным рекомендациям, skill gap, roadmap, профессиям, курсам и вашим результатам в системе.",
    "kk": "Мен тек мансап ұсыныстары, skill gap, оқу жоспары, мамандықтар, курстар және жүйедегі нәтижелер бойынша көмектесе аламын.",
    "en": "I can only help with career recommendations, skill gaps, learning roadmaps, professions, courses, and your system results.",
}

app = FastAPI(title='CareerFlow API')
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], 
    allow_methods=['*'],
    allow_headers=['*'],
)

classifier = None
demand = None
skill_matcher = None
course_finder = None
llm = None


def get_classifier():
    global classifier
    if classifier is None:
        from services.classifier import ClassifierService

        classifier = ClassifierService()
    return classifier


def get_demand():
    global demand
    if demand is None:
        from services.demand import DemandService

        demand = DemandService()
    return demand


def get_skill_matcher():
    global skill_matcher
    if skill_matcher is None:
        from services.skill_matcher import SkillMatcherService

        skill_matcher = SkillMatcherService()
    return skill_matcher


def get_course_finder():
    global course_finder
    if course_finder is None:
        from services.course_finder import CourseFinderService

        course_finder = CourseFinderService()
    return course_finder


def get_llm():
    global llm
    if llm is None:
        from services.llm import LLMService

        llm = LLMService()
    return llm


def get_llm_credentials(request: Request) -> tuple[str, str]:
    # Read manually so validation errors never echo secret headers in a 422 body.
    try:
        return validate_credentials(
            request.headers.get("x-llm-provider", ""),
            request.headers.get("x-llm-api-key", ""),
        )
    except LLMError as error:
        raise HTTPException(status_code=error.status_code, detail={
            "code": error.code, "message": str(error),
        }) from None


def llm_http_error(error: Exception) -> HTTPException:
    safe = safe_llm_error(error)
    return HTTPException(status_code=safe.status_code, detail={"code": safe.code, "message": str(safe)})


def _is_career_chat_allowed(message: str) -> bool:
    text = (message or "").lower()
    if any(pattern in text for pattern in PROMPT_INJECTION_PATTERNS):
        return False
    has_career_context = any(keyword in text for keyword in CAREER_TOPIC_KEYWORDS)
    if any(pattern in text for pattern in OFF_TOPIC_PATTERNS) and not has_career_context:
        return False
    return True


def _off_topic_response(lang: str) -> str:
    return OFF_TOPIC_RESPONSES.get(lang, OFF_TOPIC_RESPONSES["en"])


def _get_frontend_asset(full_path: str) -> Path | None:
    candidate = (FRONTEND_BUILD_DIR / full_path).resolve()
    try:
        candidate.relative_to(FRONTEND_BUILD_DIR)
    except ValueError:
        return None

    if candidate.is_file():
        return candidate
    return None


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/parse-resume')
async def parse_resume(request: Request):
    filename = unquote(request.headers.get("x-filename", "resume"))
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Empty resume file.")

    try:
        from services.resume_parser import extract_text_from_upload, parse_resume_text

        text = extract_text_from_upload(filename, content)
        parsed = parse_resume_text(text)
        return {
            "filename": filename,
            **parsed,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not parse resume: {e}")


@app.post('/recommend')
def recommend(profile: StudentProfile):
    try:
        skill_matcher_service = get_skill_matcher()
        classifier_service = get_classifier()
        demand_service = get_demand()
        course_finder_service = get_course_finder()
        llm_service = get_llm()

        # 1. Skill Matcher
        skill_scores = skill_matcher_service.get_scores(profile.skills)
        user_skills_ranked = skill_matcher_service.get_user_skills_ranked(profile.skills)

        # 2. Classifier 
        profile_dict = profile.model_dump(exclude={'skills', 'lang'})
        classification_scores = classifier_service.get_scores(profile_dict)
        skill_explanations = (
            classifier_service.get_skill_explanations(
                profile=profile_dict,
                student_skills=profile.skills,
            )
            if hasattr(classifier_service, "get_skill_explanations")
            else {}
        )

        # 3. Demand
        demand_scores = demand_service.get_scores()

        # 4. Weighted scoring to get top profession + alternative
        top_profession, final_scores, top_2 = get_top_profession(
            classification_scores=classification_scores,
            demand_scores=demand_scores,
            skill_scores=skill_scores
        )

        # 5. Personalized roadmap + courses
        roadmap_with_courses, full_roadmap = course_finder_service.get_roadmap_with_courses(
            profession=top_profession,
            student_skills=profile.skills,
            lang=profile.lang,
        )
        roadmaps_by_profession = (
            course_finder_service.get_gap_summary_for_all(profile.skills, lang=profile.lang)
            if hasattr(course_finder_service, "get_gap_summary_for_all")
            else {top_profession: {"full": full_roadmap, "gap": {}, "roadmap_with_courses": roadmap_with_courses}}
        )

        # 6. LLM Context Building
        context = llm_service.build_context(
            skills=profile.skills,
            skill_scores=skill_scores,
            classification_scores=classification_scores,
            demand_scores=demand_scores,
            roadmap_with_courses=roadmap_with_courses,
        )
        session_id = str(uuid4())
        session_store[session_id] = context

        # Get SHAP explanations for top profession
        top_prof_explanation = skill_explanations.get(top_profession, {})
        top_prof_shap = top_prof_explanation.get("shap_explanations", [])

        response_payload = {
            'top_profession':        top_profession,
            'session_id':            session_id,
            'alternative_profession': top_2[1],  
            'final_scores':         final_scores,
            'skill_scores':          skill_scores,
            'classification_scores': classification_scores,
            'demand_scores':         demand_scores,
            'skill_explanations':    skill_explanations,
            'shap_explanations':     top_prof_shap,
            'scoring_weights': {
                'classifier': CLASSIFIER_COEF,
                'skill_matcher': SKILL_MATCHER_COEF,
                'demand_trend': DEMAND_TREND_COEF,
                'demand_market_share': DEMAND_MARKET_SHARE_COEF,
            },
            'user_skills_ranked':    user_skills_ranked,
            'roadmap_with_courses':  roadmap_with_courses,
            'full_roadmap':          full_roadmap,
            'roadmaps_by_profession': roadmaps_by_profession,
            'context':               context,
            '_formData':             profile.model_dump(),
        }

        save_recommendation_session(
            session_id=session_id,
            user_id=DEMO_USER_ID,
            profile=profile.model_dump(),
            result_payload=response_payload,
            context=context,
            roadmaps_by_profession=roadmaps_by_profession,
            roadmap_with_courses=roadmap_with_courses,
        )

        return response_payload

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/courses/filter")
def filter_courses(
    skills_gaps: list[str] = Body(..., description="Плоский список навыков из gap"),
    lang: str = Body("en", description="Язык фильтрации"),
    filters: dict[str, Any] = Body(..., description="Словарь с выбранными фильтрами")
):
    course_finder_service = get_course_finder()
    updated_courses = course_finder_service.update_courses_by_filters(
        skills_gaps=skills_gaps, 
        lang=lang, 
        filters=filters
    )
    return {
        "courses_by_skills": updated_courses
    }


@app.get('/recommendation/history')
def recommendation_history(user_id: str = DEMO_USER_ID, limit: int = 12):
    return {'items': list_recommendation_history(user_id=user_id, limit=limit)}


@app.delete('/recommendation/history')
def clear_recommendation_history(user_id: str = DEMO_USER_ID):
    return delete_recommendation_history(user_id=user_id)


@app.get('/recommendation/{session_id}/state')
def recommendation_state(session_id: str, user_id: str = DEMO_USER_ID):
    state = get_recommendation_state(session_id=session_id, user_id=user_id)
    if state is None:
        raise HTTPException(status_code=404, detail='Recommendation session not found.')
    return state


@app.put('/recommendation/{session_id}/progress')
def save_roadmap_progress(session_id: str, request: RoadmapProgressRequest, user_id: str = DEMO_USER_ID):
    saved = update_recommendation_progress(
        session_id=session_id,
        user_id=user_id,
        done_skills=request.doneSkills,
        category_order=request.categoryOrder,
        skill_orders=request.skillOrders,
        selected_profession=request.selectedProfession,
    )
    if not saved.get('saved'):
        raise HTTPException(status_code=404, detail='Recommendation session not found.')
    return saved


@app.put('/recommendation/{session_id}/course-filters')
def save_course_filters(session_id: str, request: CourseFilterPreferencesRequest):
    saved = save_course_filter_preferences(
        session_id=session_id,
        user_id=request.user_id or DEMO_USER_ID,
        filters=request.filters,
    )
    if not saved.get('saved'):
        raise HTTPException(status_code=404, detail='Recommendation session not found.')
    return saved


@app.post('/chat')
def chat(request: ChatRequest, credentials: tuple[str, str] = Depends(get_llm_credentials)):
    if not _is_career_chat_allowed(request.message):
        return {'response': _off_topic_response(request.lang)}

    provider, api_key = credentials
    try:
        response = get_llm().chat(
            context=session_store.get(request.session_id, "No context available."),
            history=[item.model_dump() for item in request.history],
            message=request.message, provider=provider, api_key=api_key,
        )
        return {'response': response}
    except Exception as error:
        raise llm_http_error(error) from None


@app.post('/voice/transcribe')
async def transcribe_voice(
    request: Request, lang: str = 'en',
    credentials: tuple[str, str] = Depends(get_llm_credentials),
):
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio.")

    provider, api_key = credentials
    mime_type = request.headers.get("content-type", "audio/wav").split(";")[0] or "audio/wav"
    try:
        # The SDK is synchronous; keep provider I/O off the event loop.
        from starlette.concurrency import run_in_threadpool

        text = await run_in_threadpool(
            get_llm().transcribe_audio, content, mime_type=mime_type, lang=lang,
            provider=provider, api_key=api_key,
        )
        return {"text": text}
    except Exception as error:
        raise llm_http_error(error) from None


@app.post('/chat/stream')
def chat_stream(request: ChatRequest, credentials: tuple[str, str] = Depends(get_llm_credentials)):
    provider, api_key = credentials
    context = session_store.get(request.session_id, "No context available.")

    def generate():
        try:
            if not _is_career_chat_allowed(request.message):
                yield f"data: {json.dumps({'type': 'text', 'content': _off_topic_response(request.lang)})}\n\n"
            else:
                # StreamingResponse advances sync iterators in its thread pool.
                yield from (
                    f"data: {chunk}\n\n"
                    for chunk in get_llm().chat_stream(
                        context=context, history=[item.model_dump() for item in request.history],
                        message=request.message, deep=request.deep, provider=provider, api_key=api_key,
                    )
                )
        except Exception as error:
            safe = safe_llm_error(error)
            yield f"data: {json.dumps({'type': 'error', 'code': safe.code, 'content': str(safe)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get('/', include_in_schema=False)
def serve_frontend():
    index_path = FRONTEND_BUILD_DIR / 'index.html'
    if not index_path.exists():
        raise HTTPException(
            status_code=404,
            detail='Frontend build not found. Build frontend or run it separately.',
        )
    return FileResponse(index_path, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})


@app.get('/{full_path:path}', include_in_schema=False)
def serve_frontend_routes(full_path: str):
    index_path = FRONTEND_BUILD_DIR / 'index.html'
    if not index_path.exists():
        raise HTTPException(
            status_code=404,
            detail='Frontend build not found. Build frontend or run it separately.',
        )

    asset_path = _get_frontend_asset(full_path)
    if asset_path:
        return FileResponse(asset_path)
    return FileResponse(index_path, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
