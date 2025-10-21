from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from pymongo.errors import OperationFailure
import signal
from routers import (
    users_router,
    activities_router,
    groups_router,
    exports_router,
    imports_router,
    logs_router,
    activities_v2_router,
    users_v2_router,
    groups_v2_router,
    activity_statistics_router,
    times_router,
    mcp_router,
)
from database import close_mongo_connection, connect_to_mongo
import socketio
from fastapi.middleware.cors import CORSMiddleware
from database import db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from tasks.compute_time import compute_tasks, generate_reports
from tasks.data_fix import wash_data

scheduler = AsyncIOScheduler()
sio = socketio.AsyncServer(async_mode="asgi")
socket = socketio.ASGIApp(sio)

app = FastAPI(default_response_class=JSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://v4.zvms.site",
        "https://v4-netlify.zvms.site",
        "https://main--zvms.netlify.app",
    ],
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
        {"$set": {"status": "failed", "errmsg": "Program interrupted unexpectedly"}},
    )


async def startup_event():
    """Startup event handler to initialize the application."""
    print("Starting up...")
    await connect_to_mongo()
    scheduler.start()

    # Schedule compute_time to run daily at 00:00 HKT (UTC+8)
    scheduler.add_job(
        compute_tasks,
        "cron",
        hour=1,
        minute=0,
        second=0,
        timezone="Asia/Hong_Kong",
        id="daily_compute_time",
    )

    # Schedule compute_time to run daily at 00:00 HKT (UTC+8)
    scheduler.add_job(
        wash_data,
        "cron",
        hour=2,
        minute=0,
        second=0,
        timezone="Asia/Hong_Kong",
        id="daily_wash_data",
    )

    # Schedule compute_time to run daily at 00:00 HKT (UTC+8)
    scheduler.add_job(
        generate_reports,
        "cron",
        hour=4,
        minute=0,
        second=0,
        timezone="Asia/Hong_Kong",
        id="daily_generate_reports",
    )

    print("Application started.")
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_event()))
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_event()))


async def shutdown_event():
    """Shutdown event handler to clean up resources."""
    print("Shutting down...")
    await mark_all_tasks_failed()
    scheduler.shutdown()
    await close_mongo_connection()
    print("Application shut down.")


# Register events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

# Register routes
app.include_router(users_router.router, prefix="/api/users", tags=["users"])
app.include_router(
    activities_router.router, prefix="/api/activities", tags=["activities"]
)
app.include_router(groups_router.router, prefix="/api/groups", tags=["groups"])
app.include_router(exports_router.router, prefix="/api/exports", tags=["exports"])
app.include_router(imports_router.router, prefix="/api/imports", tags=["imports"])
app.include_router(logs_router.router, prefix="/api/logs", tags=["logs"])

app.include_router(activities_v2_router.router, prefix="/api/v2/activities")
app.include_router(users_v2_router.router, prefix="/api/v2/users")
app.include_router(groups_v2_router.router, prefix="/api/v2/groups")
app.include_router(times_router.router, prefix="/api/v2/times")
app.include_router(
    activity_statistics_router.router, prefix="/api/v2/statistics/activities"
)
app.include_router(mcp_router.router, prefix="/api/v2/mcp")


@app.get("/api/")
async def home():
    return {
        "status": "ok",
        "code": 200,
        "data": {
            "message": "Welcome to ZVMS API",
            "version": "4.1",
            "author": "ZZDev",
            "license": "MIT",
            "source": "https://github.com/zvms/zvms4-backend-python.git",
            "apis": {
                "user": "/api/users",
                "activity": "/api/activities",
                "group": "/api/groups",
                "exports": "/api/exports",
                "imports": "/api/imports",
                "logs": "/api/logs",
            },
        },
    }


# Redirect singular routes to plural routes
@app.api_route("/api/user/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def redirect_user(request: Request, path: str):
    new_url = request.url.replace(path="/api/users/" + path)
    return RedirectResponse(url=new_url)


@app.api_route("/api/activity/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def redirect_activity(request: Request, path: str):
    new_url = request.url.replace(path="/api/activities/" + path)
    return RedirectResponse(url=new_url)


@app.api_route("/api/group/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def redirect_group(request: Request, path: str):
    new_url = request.url.replace(path="/api/groups/" + path)
    return RedirectResponse(url=new_url)


@app.api_route("/api/export/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def redirect_export(request: Request, path: str):
    new_url = request.url.replace(path="/api/exports/" + path)
    return RedirectResponse(url=new_url)


@app.api_route("/api/import/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def redirect_import(request: Request, path: str):
    new_url = request.url.replace(path="/api/imports/" + path)
    return RedirectResponse(url=new_url)


@app.api_route("/api/log/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def redirect_log(request: Request, path: str):
    new_url = request.url.replace(path="/api/logs/" + path)
    return RedirectResponse(url=new_url)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check MongoDB connection
        await db.zvms.command("ping")
        return {"status": "ok", "code": 200, "data": "OK"}
    except Exception as e:
        return {"status": "error", "code": 500, "data": str(e)}


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
async def generic_exception_handler(_: Request, exc: Exception):
    """Catch-all exception handler to return a generic error message."""
    return JSONResponse(
        content={"detail": "An internal server error occurred: %s" % type(exc).__name__}, status_code=500
    )


@app.exception_handler(OperationFailure)
async def operation_failure_exception_handler(_: Request, exc: OperationFailure):
    """Catch-all exception handler to return a generic error message."""
    return JSONResponse(content={"detail": exc.details["errmsg"]}, status_code=400)


@app.get("/api/version")
async def get_version():
    return {"status": "ok", "code": 200, "data": "4.1"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0", port=8000)
