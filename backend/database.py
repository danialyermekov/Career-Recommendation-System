import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH


DEMO_USER_ID = "demo"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recommendation_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                top_profession TEXT NOT NULL,
                alternative_profession TEXT,
                profile_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                context TEXT,
                progress_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS specialization_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                profession TEXT NOT NULL,
                final_score REAL,
                skill_score REAL,
                classification_score REAL,
                trend_score REAL,
                market_share REAL,
                predicted_vacancies REAL,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, profession),
                FOREIGN KEY (session_id) REFERENCES recommendation_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS skill_gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                profession TEXT NOT NULL,
                category TEXT NOT NULL,
                skill TEXT NOT NULL,
                is_missing INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, profession, category, skill),
                FOREIGN KEY (session_id) REFERENCES recommendation_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS roadmap_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                profession TEXT NOT NULL,
                category TEXT NOT NULL,
                skill TEXT NOT NULL,
                category_position INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL DEFAULT 0,
                is_done INTEGER NOT NULL DEFAULT 0,
                courses_json TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL,
                UNIQUE(session_id, profession, category, skill),
                FOREIGN KEY (session_id) REFERENCES recommendation_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS course_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                category TEXT NOT NULL,
                skill TEXT NOT NULL,
                course_title TEXT NOT NULL,
                platform TEXT,
                course_url TEXT,
                is_started INTEGER NOT NULL DEFAULT 0,
                is_completed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(session_id, category, skill, course_title, platform),
                FOREIGN KEY (session_id) REFERENCES recommendation_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS course_filter_preferences (
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                filters_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, session_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES recommendation_sessions(id) ON DELETE CASCADE
            );
            """
        )
        ensure_user(conn)


def ensure_user(conn: sqlite3.Connection, user_id: str = DEMO_USER_ID, display_name: str = "Demo User") -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO users (id, display_name, created_at)
        VALUES (?, ?, ?)
        """,
        (user_id, display_name, _now()),
    )


def save_recommendation_session(
    *,
    session_id: str,
    user_id: str,
    profile: dict,
    result_payload: dict,
    context: str,
    roadmaps_by_profession: dict,
    roadmap_with_courses: dict,
) -> None:
    now = _now()
    init_db()
    with get_connection() as conn:
        ensure_user(conn, user_id)
        conn.execute(
            """
            INSERT INTO recommendation_sessions (
                id, user_id, top_profession, alternative_profession,
                profile_json, result_json, context, progress_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT progress_json FROM recommendation_sessions WHERE id = ?), '{}'), ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id = excluded.user_id,
                top_profession = excluded.top_profession,
                alternative_profession = excluded.alternative_profession,
                profile_json = excluded.profile_json,
                result_json = excluded.result_json,
                context = excluded.context,
                updated_at = excluded.updated_at
            """,
            (
                session_id,
                user_id,
                result_payload.get("top_profession"),
                result_payload.get("alternative_profession"),
                _json_dumps(profile),
                _json_dumps(result_payload),
                context,
                session_id,
                now,
                now,
            ),
        )

        conn.execute("DELETE FROM specialization_scores WHERE session_id = ?", (session_id,))
        final_scores = result_payload.get("final_scores", {})
        skill_scores = result_payload.get("skill_scores", {})
        classification_scores = result_payload.get("classification_scores", {})
        demand_scores = result_payload.get("demand_scores", {})
        for profession, final_score in final_scores.items():
            demand = demand_scores.get(profession, {}) or {}
            conn.execute(
                """
                INSERT INTO specialization_scores (
                    session_id, profession, final_score, skill_score, classification_score,
                    trend_score, market_share, predicted_vacancies, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    profession,
                    final_score,
                    skill_scores.get(profession),
                    classification_scores.get(profession),
                    demand.get("trend_score"),
                    demand.get("market_share"),
                    demand.get("predicted_vacancies"),
                    now,
                ),
            )

        conn.execute("DELETE FROM skill_gaps WHERE session_id = ?", (session_id,))
        for profession, summary in (roadmaps_by_profession or {}).items():
            full = summary.get("full", {}) or {}
            gap = summary.get("gap", {}) or {}
            missing = {
                (category, skill)
                for category, skills in gap.items()
                for skill in (skills or [])
            }
            for category, skills in full.items():
                for skill in skills or []:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO skill_gaps (
                            session_id, profession, category, skill, is_missing, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            profession,
                            category,
                            skill,
                            1 if (category, skill) in missing else 0,
                            now,
                        ),
                    )

        conn.execute("DELETE FROM roadmap_items WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM course_progress WHERE session_id = ?", (session_id,))
        top_profession = result_payload.get("top_profession")
        for category_position, (category, skill_map) in enumerate((roadmap_with_courses or {}).items()):
            for position, (skill, data) in enumerate((skill_map or {}).items()):
                courses = data.get("courses", []) if isinstance(data, dict) else []
                conn.execute(
                    """
                    INSERT OR REPLACE INTO roadmap_items (
                        session_id, profession, category, skill, category_position,
                        position, is_done, courses_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        session_id,
                        top_profession,
                        category,
                        skill,
                        category_position,
                        position,
                        _json_dumps(courses),
                        now,
                    ),
                )
                for course in courses:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO course_progress (
                            session_id, category, skill, course_title, platform,
                            course_url, is_started, is_completed, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
                        """,
                        (
                            session_id,
                            category,
                            skill,
                            course.get("title") or "",
                            course.get("platform"),
                            course.get("course_url"),
                            now,
                        ),
                    )


def list_recommendation_history(user_id: str = DEMO_USER_ID, limit: int = 12) -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, top_profession, result_json, progress_json, created_at, updated_at
            FROM recommendation_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    history = []
    for row in rows:
        progress = _json_loads(row["progress_json"], {})
        result = _json_loads(row["result_json"], {})
        selected = progress.get("selectedProfession") or result.get("top_profession") or row["top_profession"]
        history.append(
            {
                "id": row["id"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "top_profession": row["top_profession"],
                "selectedProfession": selected,
                "results": result,
                "progress": {
                    "done": progress.get("doneSkills", progress.get("done", [])),
                    "categoryOrder": progress.get("categoryOrder", []),
                    "skillOrders": progress.get("skillOrders", {}),
                },
            }
        )
    return history


def get_recommendation_state(session_id: str, user_id: str = DEMO_USER_ID) -> dict | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT result_json, progress_json
            FROM recommendation_sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()
        filters = conn.execute(
            """
            SELECT filters_json
            FROM course_filter_preferences
            WHERE session_id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()
    if not row:
        return None
    return {
        "results": _json_loads(row["result_json"], {}),
        "progress": _json_loads(row["progress_json"], {}),
        "filters": _json_loads(filters["filters_json"], {}) if filters else {},
    }


def update_recommendation_progress(
    *,
    session_id: str,
    user_id: str,
    done_skills: list[str],
    category_order: list[str],
    skill_orders: dict,
    selected_profession: str | None = None,
) -> dict:
    now = _now()
    progress = {
        "doneSkills": done_skills,
        "categoryOrder": category_order,
        "skillOrders": skill_orders,
        "selectedProfession": selected_profession,
    }
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM recommendation_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not row:
            return {"saved": False}

        conn.execute(
            """
            UPDATE recommendation_sessions
            SET progress_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (_json_dumps(progress), now, session_id, user_id),
        )
        done = set(done_skills or [])
        conn.execute("UPDATE roadmap_items SET is_done = 0 WHERE session_id = ?", (session_id,))
        for key in done:
            if "::" not in key:
                continue
            category, skill = key.split("::", 1)
            conn.execute(
                """
                UPDATE roadmap_items
                SET is_done = 1, updated_at = ?
                WHERE session_id = ? AND category = ? AND skill = ?
                """,
                (now, session_id, category, skill),
            )
        for category_position, category in enumerate(category_order or []):
            conn.execute(
                """
                UPDATE roadmap_items
                SET category_position = ?, updated_at = ?
                WHERE session_id = ? AND category = ?
                """,
                (category_position, now, session_id, category),
            )
        for category, skills in (skill_orders or {}).items():
            for position, skill in enumerate(skills or []):
                conn.execute(
                    """
                    UPDATE roadmap_items
                    SET position = ?, updated_at = ?
                    WHERE session_id = ? AND category = ? AND skill = ?
                    """,
                    (position, now, session_id, category, skill),
                )
    return {"saved": True, "progress": progress}


def save_course_filter_preferences(
    *,
    session_id: str,
    user_id: str,
    filters: dict,
) -> dict:
    now = _now()
    init_db()
    with get_connection() as conn:
        ensure_user(conn, user_id)
        session = conn.execute(
            "SELECT id FROM recommendation_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not session:
            return {"saved": False}
        conn.execute(
            """
            INSERT INTO course_filter_preferences (user_id, session_id, filters_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, session_id) DO UPDATE SET
                filters_json = excluded.filters_json,
                updated_at = excluded.updated_at
            """,
            (user_id, session_id, _json_dumps(filters), now),
        )
    return {"saved": True, "filters": filters}


def delete_recommendation_history(user_id: str = DEMO_USER_ID) -> dict:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM recommendation_sessions WHERE user_id = ?", (user_id,))
    return {"deleted": True}
