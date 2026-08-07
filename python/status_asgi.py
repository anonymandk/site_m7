import json
import asyncio
from typing import Callable

from smart_router import SmartRouter

# Create a router instance and start background initialization.
router = SmartRouter()
try:
    asyncio.get_event_loop().create_task(router.initialize())
except RuntimeError:
    # If no event loop is running at import time, that's fine — servers like
    # uvicorn will start the loop and initialize when first awaited.
    pass


async def app(scope, receive, send):
    if scope["type"] != "http":
        await send({"type": "http.response.start", "status": 500, "headers": []})
        await send({"type": "http.response.body", "body": b"Unsupported scope"})
        return

    path = scope.get("path", "")
    method = scope.get("method", "GET").upper()

    if path == "/status" and method == "GET":
        body = json.dumps(router.status(), ensure_ascii=False).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})
        return

    # Not found
    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"Not found"})
