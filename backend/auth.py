"""Supabase Auth verifies tokens server-side for every authenticated request."""
from uuid import UUID
import httpx
from fastapi import Depends, HTTPException, Request
from config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY
import database

def verify_access_token(token: str) -> dict:
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(503, "Authentication is not configured.")
    try:
        # Auth /user validates signatures, expiry and the live user for all signing modes.
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{SUPABASE_URL}/auth/v1/user", headers={
                "apikey": SUPABASE_PUBLISHABLE_KEY, "Authorization": f"Bearer {token}"})
        if response.status_code in {401, 403}:
            raise HTTPException(401, "Invalid or expired access token.")
        if response.status_code != 200:
            raise HTTPException(503, "Authentication is temporarily unavailable.")
        data = response.json()
        user_id = str(UUID(data["id"]))
        name = data.get("user_metadata", {}).get("full_name") or data.get("user_metadata", {}).get("name") or "CareerFlow user"
        return {"id": user_id, "display_name": str(name)[:200]}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Authentication is temporarily unavailable.") from None

def optional_user(request: Request):
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 8192:
        raise HTTPException(401, "Invalid access token.")
    user = verify_access_token(token)
    database.ensure_user(user)
    if database.is_deleting(user["id"]) and request.url.path != "/account":
        raise HTTPException(403, "Account deletion is pending. Retry deletion from your account page.")
    return user

def require_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(401, "Sign in to access your account.")
    return user

def delete_auth_user(user_id: str):
    if not SUPABASE_SECRET_KEY:
        raise HTTPException(503, "Account deletion requires server configuration. Contact contact@careerflow.live.")
    try:
        with httpx.Client(timeout=15) as client:
            response = client.delete(f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}", headers={
                "apikey": SUPABASE_SECRET_KEY, "Authorization": f"Bearer {SUPABASE_SECRET_KEY}"})
        if response.status_code not in {200, 204, 404}:
            raise HTTPException(503, "Account deletion is pending. Please retry or contact support.")
    except httpx.HTTPError:
        raise HTTPException(503, "Account deletion is pending. Please retry or contact support.") from None
