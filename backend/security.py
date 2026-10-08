from collections import deque
from threading import Lock
from time import monotonic
from starlette.responses import JSONResponse

# shortcut: limits are per process/IP; keep one worker and add edge limits before scaling.
buckets = {}
lock = Lock()

class PublicRequestLimits:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "DELETE"}:
            return await self.app(scope, receive, send)
        path = scope["path"]
        limit = 5 if path == "/feedback" else 30
        key = (scope.get("client", ("unknown",))[0], path.split('/')[1])
        current = monotonic()
        with lock:
            for old in [k for k, times in buckets.items() if not times or times[-1] < current - 60]:
                del buckets[old]
            times = buckets.setdefault(key, deque())
            while times and times[0] < current - 60:
                times.popleft()
            blocked = len(times) >= limit or len(buckets) > 10000
            if not blocked:
                times.append(current)
        if blocked:
            return await JSONResponse({"detail": "Too many requests. Try again shortly."}, 429, headers={"Retry-After": "60"})(scope, receive, send)
        maximum = 8 * 1024 * 1024 if path in {"/parse-resume", "/voice/transcribe"} else 1024 * 1024
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > maximum:
                return await JSONResponse({"detail": "Request too large."}, 413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)
