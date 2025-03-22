from fastapi import Request, Response, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import OperationFailure

from routers import (
    users_router,
    activities_router,
    groups_router,
    exports_router,
    imports_router,
    logs_router
)
from database import close_mongo_connection, connect_to_mongo
import socketio
from fastapi.middleware.cors import CORSMiddleware
from database import db

sio = socketio.AsyncServer(async_mode="asgi")
socket = socketio.ASGIApp(sio)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://v4.zvms.site", "https://v4-netlify.zvms.site", "https://deploy-preview-64--zvms.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/socket.io", socket)

@sio.event
async def connect(sid, environ):
    print(f"connect {sid}")


@sio.event
async def disconnect(sid):
    print(f"disconnect {sid}")


async def mark_all_tasks_failed():
    await db.zvms.tasks.update_many(
        {"status": {"$ne": "completed"}},
        {"$set": {"status": "failed", "errmsg": "Program interrupted unexpectedly"}}
    )


# Register events
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# Register routes
app.include_router(users_router.router, prefix="/api/users", tags=["users"])
app.include_router(
    activities_router.router, prefix="/api/activities", tags=["activities"]
)
app.include_router(groups_router.router, prefix="/api/groups", tags=["groups"])
app.include_router(exports_router.router, prefix='/api/exports', tags=['exports'])
app.include_router(imports_router.router, prefix='/api/imports', tags=['imports'])
app.include_router(logs_router.router, prefix='/api/logs', tags=['logs'])

@app.router.get("/api/")
async def home():
    return {"status": "ok", "code": 200, "data": {
        "message": "Welcome to ZVMS API",
        "version": "0.1.0-alpha.1",
        "author": "ZZDev",
        "license": "MIT",
        "source": "https://github.com/zvms/zvms4-backend-python.git",
        "apis": {
            "user": "/api/users",
            "activity": "/api/activities",
            "group": "/api/groups",
            "exports": "/api/exports",
            "imports": "/api/imports",
            "logs": "/api/logs"
        }
    }}


@app.get("/api/cert")
async def get_cert():
    return {
        "status": "ok",
        "code": 200,
        "data": open("./rsa_public_key.pem", "r").read(),
    }

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Convert Pydantic errors to a readable string for frontend display."""
    errors = exc.errors()
    formatted_errors = []

    for error in errors:
        field = " → ".join(map(str, error["loc"]))  # Format location as "body → field"
        message = error["msg"]
        formatted_errors.append(f"{field}: {message}")

    error_string = "\n".join(formatted_errors)  # Combine into a single string
    return JSONResponse(content={"detail": error_string}, status_code=422)


@app.exception_handler(Exception)
async def generic_exception_handler():
    """Catch-all exception handler to return a generic error message."""
    return JSONResponse(
        content={"detail": "An internal server error occurred"}, status_code=500
    )

@app.exception_handler(OperationFailure)
async def operation_failure_exception_handler(_: Request, exc: OperationFailure):
    """Catch-all exception handler to return a generic error message."""
    return JSONResponse(
        content={"detail": exc.details['errmsg']}, status_code=400
    )

@app.get("/api/version")
async def get_version():
    return {"status": "ok", "code": 200, "data": "0.1.0-alpha.1"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0", port=8000)
