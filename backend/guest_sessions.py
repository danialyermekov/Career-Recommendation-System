from copy import deepcopy
from hashlib import sha256
from threading import Lock
from time import monotonic
from fastapi import HTTPException, Request

# shortcut: temporary guest state is process-local; use a shared TTL store before adding workers.
sessions = {}
lock = Lock()
TTL = 7200
MAX_SESSIONS = 200

def guest_owner(request: Request):
    token = request.headers.get("x-guest-token", "")
    if len(token) < 32 or len(token) > 128 or not token.isascii() or not token.isalnum():
        raise HTTPException(401, "A guest session credential is required.")
    return sha256(token.encode()).hexdigest()

def _prune():
    for key in [key for key, value in sessions.items() if value["expires"] < monotonic()]:
        del sessions[key]

def save(session_id, owner, result):
    with lock:
        _prune()
        if len(sessions) >= MAX_SESSIONS:
            raise HTTPException(503, "Guest capacity reached. Please try again later.")
        sessions[session_id] = {"owner": owner, "expires": monotonic() + TTL, "state": {"results": deepcopy(result), "progress": {}, "filters": {}}}

def state(session_id, owner, *, progress=None, filters=None):
    with lock:
        _prune()
        value = sessions.get(session_id)
        if not value or value["owner"] != owner:
            raise HTTPException(404, "Recommendation session not found.")
        if progress is not None:
            value["state"]["progress"] = progress
        if filters is not None:
            value["state"]["filters"] = filters
        return deepcopy(value["state"])
