from fastapi import Request, Response, FastAPI
from fastapi.exceptions import RequestValidationError
from routers import (
    notifications_router,
    users_router,
    activities_router,
    groups_router,
    trophies_router,
    plugins_router,
    exports_router,
    imports_router
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
    allow_origins=["http://localhost:5173", "https://v4.zvms.site", "https://v4-netlify.zvms.site/"],
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
app.include_router(users_router.router, prefix="/api/user", tags=["users"])
app.include_router(
    activities_router.router, prefix="/api/activity", tags=["activities"]
)
app.include_router(
    notifications_router.router, prefix="/api/notification", tags=["notifications"]
)
app.include_router(groups_router.router, prefix="/api/group", tags=["groups"])
app.include_router(trophies_router.router, prefix="/api/trophy", tags=["trophies"])
app.include_router(plugins_router.router, prefix='/api/plugin', tags=['plugins', 'calculator', 'dictionary'])
app.include_router(exports_router.router, prefix='/api/exports', tags=['exports'])
app.include_router(imports_router.router, prefix='/api/imports', tags=['imports'])

@app.router.get("/api/")
async def home():
    return {"status": "ok", "code": 200, "data": {
        "message": "Welcome to ZVMS API",
        "version": "0.1.0-alpha.1",
        "author": "ZZDev",
        "license": "MIT",
        "source": "https://github.com/zvms/zvms4-backend-python.git",
        "apis": {
            "user": "/api/user",
            "activity": "/api/activity",
            "notification": "/api/notification",
            "group": "/api/group",
            "trophy": "/api/trophy",
            "plugin": "/api/plugin",
            "exports": "/api/exports",
            "imports": "/api/imports"
        }
    }}


# Custom exception handler for internal server errors
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return Response(
        status_code=500,
        content={"message": "An internal server error occurred"},
    )


# Optional: Handle validation errors specifically, if desired
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return Response(
        status_code=422,
        content={"message": "Validation error", "details": exc.errors()},
    )


@app.get("/api/cert")
async def get_cert():
    return {
        "status": "ok",
        "code": 200,
        "data": open("./rsa_public_key.pem", "r").read(),
    }


@app.get("/api/version")
async def get_version():
    return {"status": "ok", "code": 200, "data": "0.1.0-alpha.1"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0", port=8000)
