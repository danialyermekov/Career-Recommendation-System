from pathlib import Path
from urllib.parse import unquote
from typing import Any
from fastapi import FastAPI, HTTPException, Request, Response, Body, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from schemas import StudentProfile, ChatRequest, RoadmapProgressRequest, CourseFilterPreferencesRequest, FeedbackRequest, FeedbackVoteRequest
from auth import optional_user, require_user, delete_auth_user
import auth
import database
import guest_sessions
from security import PublicRequestLimits
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from config import CORS_ORIGINS
import json
import logging
from services.llm import LLMError, safe_llm_error, validate_credentials
from services import ai_trial
from schemas import TrialRequest
from top_profession import get_top_profession
from config import CLASSIFIER_COEF, SKILL_MATCHER_COEF, DEMAND_TREND_COEF, DEMAND_MARKET_SHARE_COEF
from uuid import uuid4
from uuid import UUID
from typing import Literal
from database import (
    delete_recommendation_history,
    get_recommendation_state,
    list_recommendation_history,
    save_course_filter_preferences,
    save_recommendation_session,
    update_recommendation_progress,
)

FRONTEND_BUILD_DIR = (Path(__file__).resolve().parent.parent / 'frontend' / 'build').resolve()
PUBLIC_PAGES = {'', 'about', 'feedback', 'changelog', 'roadmap', 'privacy', 'terms', 'contact', 'disclaimer'}
CANONICAL_ORIGIN = 'https://careerflow.live'
PUBLIC_ASSETS = {
    'robots.txt', 'sitemap.xml', 'favicon.ico', 'favicon-16x16.png', 'favicon-32x32.png',
    'favicon-48x48.png', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'careerflow-og.png', 'manifest.json',
}

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


@app.middleware('http')
async def indexing_and_canonical_host(request: Request, call_next):
    # Uvicorn must trust only the actual ingress addresses for forwarded scheme handling.
    if request.url.hostname in {'careerflow.live', 'www.careerflow.live'} and (
        request.url.hostname != 'careerflow.live' or request.url.scheme != 'https'
    ):
        target = CANONICAL_ORIGIN + request.url.path
        if request.url.query:
            target += '?' + request.url.query
        return RedirectResponse(target, status_code=308)
    response = await call_next(request)
    path = request.url.path.strip('/')
    public = path in PUBLIC_PAGES and request.method in {'GET', 'HEAD'}
    asset = path.startswith(('static/', 'branding/')) or path in PUBLIC_ASSETS
    if (not public and not asset) or response.status_code >= 400 or {'code', 'error'} & request.query_params.keys():
        response.headers['X-Robots-Tag'] = 'noindex, follow'
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(SQLAlchemyError)
async def database_error(request, error):
    return JSONResponse({'detail': 'Storage is temporarily unavailable.'}, status_code=503)

@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Pydantic's default response echoes input, including CV/profile values.
    return JSONResponse({'detail': 'Invalid request fields.'}, status_code=422)

app.add_middleware(PublicRequestLimits)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'Authorization', 'X-Guest-Token', 'X-Demo-Session', 'X-Filename', 'X-LLM-Provider', 'X-LLM-API-Key'],
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
    if '..' in Path(full_path).parts or '\\' in full_path:
        return None
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


@app.get('/ready')
def ready():
    with database.get_connection() as conn:
        conn.execute(database.users.select().limit(0))
        conn.execute(database.feedback.select().limit(0))
        conn.execute(database.feedback_votes.select().limit(0))
        if ai_trial.settings()[0]:
            for table in (database.ai_trial_usage, database.ai_trial_budget, database.ai_trial_ip):
                conn.execute(table.select().limit(0))
    if not auth.SUPABASE_URL or not auth.SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(503, 'Authentication is not configured.')
    return {'status': 'ready'}


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
    except RuntimeError:
        raise HTTPException(status_code=503, detail='Resume parsing is unavailable.') from None
    except Exception:
        raise HTTPException(status_code=400, detail='Could not parse this resume.') from None


@app.post('/recommend')
def recommend(profile: StudentProfile, request: Request, user=Depends(optional_user)):
    guest = guest_sessions.guest_owner(request) if user is None else None
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

        response_payload['persistent'] = user is not None
        if user is None:
            guest_sessions.save(session_id, guest, response_payload)
            return response_payload
        save_recommendation_session(
            session_id=session_id,
            user_id=user['id'],
            profile=profile.model_dump(),
            result_payload=response_payload,
            context=context,
            roadmaps_by_profession=roadmaps_by_profession,
            roadmap_with_courses=roadmap_with_courses,
        )

        return response_payload

    except (HTTPException, SQLAlchemyError):
        raise
    except Exception:
        raise HTTPException(status_code=500, detail='Could not generate a recommendation.') from None

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
def recommendation_history(limit: int = Query(12, ge=1, le=100), user=Depends(require_user)):
    return {'items': list_recommendation_history(user_id=user['id'], limit=limit)}


@app.delete('/recommendation/history')
def clear_recommendation_history(user=Depends(require_user)):
    return delete_recommendation_history(user_id=user['id'])


@app.get('/recommendation/{session_id}/state')
def recommendation_state(session_id: str, request: Request, user=Depends(optional_user)):
    if user is None:
        return guest_sessions.state(session_id, guest_sessions.guest_owner(request))
    state = get_recommendation_state(session_id=session_id, user_id=user['id'])
    if state is None:
        raise HTTPException(status_code=404, detail='Recommendation session not found.')
    return state


@app.get('/ai/preview')
def preview_status(request: Request, response: Response, user=Depends(optional_user)):
    try:
        return ai_trial.status(request, response, user)
    except RuntimeError:
        ai_trial.error('trial_unavailable')


@app.post('/ai/preview')
def preview_chat(payload: TrialRequest, request: Request, response: Response, user=Depends(optional_user)):
    # A signed-in user can explore a temporary demo while their trial follows their account.
    if request.headers.get('x-demo-session') == 'true':
        result = guest_sessions.state(payload.session_id, guest_sessions.guest_owner(request))['results']
    else:
        result = recommendation_state(payload.session_id, request, user)['results']
    try:
        key, reservation, remaining, model = ai_trial.reserve(request, response, user)
    except RuntimeError:
        ai_trial.error('trial_unavailable')
    try:
        answer = ai_trial.answer(result, [item.model_dump() for item in payload.history], payload.message, payload.lang, model)
    except Exception as exc:
        logging.getLogger('careerflow.preview').warning('Preview generation error: %s: %s', type(exc).__name__, exc)
        ai_trial.finish(key, reservation, refund=True)
        ai_trial.error('trial_provider_failed')
    ai_trial.finish(key, reservation)
    return {'response': answer, 'remaining': remaining, 'provider': 'gemini'}


@app.put('/recommendation/{session_id}/progress')
def save_roadmap_progress(session_id: str, request: RoadmapProgressRequest, http_request: Request, user=Depends(optional_user)):
    if user is None:
        guest_sessions.state(session_id, guest_sessions.guest_owner(http_request), progress=request.model_dump())
        return {'saved': True, 'persistent': False, 'progress': request.model_dump()}
    saved = update_recommendation_progress(
        session_id=session_id,
        user_id=user['id'],
        done_skills=request.doneSkills,
        category_order=request.categoryOrder,
        skill_orders=request.skillOrders,
        selected_profession=request.selectedProfession,
    )
    if not saved.get('saved'):
        raise HTTPException(status_code=404, detail='Recommendation session not found.')
    return saved


@app.put('/recommendation/{session_id}/course-filters')
def save_course_filters(session_id: str, request: CourseFilterPreferencesRequest, http_request: Request, user=Depends(optional_user)):
    if user is None:
        guest_sessions.state(session_id, guest_sessions.guest_owner(http_request), filters=request.filters)
        return {'saved': True, 'persistent': False, 'filters': request.filters}
    saved = save_course_filter_preferences(
        session_id=session_id,
        user_id=user['id'],
        filters=request.filters,
    )
    if not saved.get('saved'):
        raise HTTPException(status_code=404, detail='Recommendation session not found.')
    return saved


@app.post('/chat')
def chat(request: ChatRequest, http_request: Request, credentials: tuple[str, str] = Depends(get_llm_credentials), user=Depends(optional_user)):
    context = recommendation_state(request.session_id, http_request, user)['results']['context']
    if not _is_career_chat_allowed(request.message):
        return {'response': _off_topic_response(request.lang)}

    provider, api_key = credentials
    try:
        response = get_llm().chat(
            context=context,
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
def chat_stream(request: ChatRequest, http_request: Request, credentials: tuple[str, str] = Depends(get_llm_credentials), user=Depends(optional_user)):
    provider, api_key = credentials
    context = recommendation_state(request.session_id, http_request, user)['results']['context']

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


@app.get('/account')
def account(user=Depends(require_user)):
    return {**user, 'deletion_pending': database.is_deleting(user['id'])}


@app.delete('/account')
def delete_account(user=Depends(require_user)):
    if not auth.SUPABASE_SECRET_KEY:
        raise HTTPException(503, 'Account deletion is not configured. Contact contact@careerflow.live.')
    database.begin_account_deletion(user['id'])
    delete_auth_user(user['id'])
    database.delete_application_user(user['id'])
    return {'deleted': True}


@app.post('/feedback', status_code=201)
def submit_feedback(payload: FeedbackRequest, request: Request, user=Depends(optional_user)):
    if payload.website:
        raise HTTPException(400, 'Feedback could not be accepted.')
    session_id = str(payload.session_id) if payload.session_id else None
    if session_id:
        recommendation_state(session_id, request, user)
    database.save_feedback({
        'type': payload.type, 'title': payload.title, 'rating': payload.rating, 'message': payload.message,
        'public_consent': payload.public_consent, 'reproduction_steps': payload.reproduction_steps,
        'session_id': session_id if user else None,
    }, user_id=user['id'] if user else None)
    return {'submitted': True}


@app.get('/api/feedback')
def public_feedback(type: Literal['review', 'feature'] = 'review', offset: int = Query(0, ge=0, le=10000),
                    user=Depends(optional_user)):
    return database.list_public_feedback(type, user_id=user['id'] if user else None, offset=offset)


@app.put('/api/feedback/{feedback_id}/vote')
def feedback_vote(feedback_id: UUID, payload: FeedbackVoteRequest, user=Depends(require_user)):
    result = database.set_feedback_vote(str(feedback_id), user['id'], payload.voted)
    if result is None:
        raise HTTPException(404, 'Feature suggestion not found.')
    return result


@app.get('/api/roadmap')
def public_roadmap():
    return database.list_public_feedback('feature', limit=100, roadmap_only=True)


@app.api_route('/', methods=['GET', 'HEAD'], include_in_schema=False)
def serve_frontend(request: Request):
    return _public_frontend('', request)


def _public_frontend(page: str, request: Request):
    callback = {'code', 'error'} & request.query_params.keys()
    index_path = FRONTEND_BUILD_DIR / ('app-shell.html' if callback else f'{page}/index.html'.lstrip('/'))
    if not index_path.exists():
        raise HTTPException(
            status_code=404,
            detail='Frontend build not found. Build frontend or run it separately.',
        )
    return FileResponse(index_path, headers={"Cache-Control": "no-cache, max-age=0, must-revalidate"})


@app.api_route('/{full_path:path}', methods=['GET', 'HEAD'], include_in_schema=False)
def serve_frontend_routes(full_path: str, request: Request):
    page = full_path.rstrip('/')
    if page in PUBLIC_PAGES:
        if full_path.endswith('/'):
            target = request.url.replace(path='/' + page)
            return RedirectResponse(str(target), status_code=308)
        return _public_frontend(page, request)
    if page == 'auth/callback':
        return FileResponse(FRONTEND_BUILD_DIR / 'app-shell.html', headers={'X-Robots-Tag': 'noindex, follow', 'Cache-Control': 'no-store'})
    allowed_asset = full_path.startswith(('static/', 'branding/')) or full_path in PUBLIC_ASSETS
    asset_path = _get_frontend_asset(full_path) if allowed_asset else None
    if asset_path:
        cache = 'public, max-age=31536000, immutable' if full_path.startswith('static/') else 'public, max-age=3600'
        media_type = 'application/xml' if full_path == 'sitemap.xml' else 'text/plain' if full_path == 'robots.txt' else None
        return FileResponse(asset_path, media_type=media_type, headers={'Cache-Control': cache})
    raise HTTPException(404, 'Page or asset not found.')
