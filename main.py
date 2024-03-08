import code
from fastapi import FastAPI, Depends, Request, Response
from bson.objectid import ObjectId
from typing import List

from fastapi.exceptions import RequestValidationError
from routers import (
    notifications_router,
    users_router,
    activities_router,
    groups_router,
    trophies_router,
    exports_router,
    images_router,
)
from fastapi import FastAPI
from database import close_mongo_connection, connect_to_mongo
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册事件
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# 注册路由
app.include_router(users_router.router, prefix="/api/user", tags=["users"])
app.include_router(
    activities_router.router, prefix="/api/activity", tags=["activities"]
)
app.include_router(
    notifications_router.router, prefix="/api/notification", tags=["notifications"]
)
app.include_router(groups_router.router, prefix="/api/group", tags=["groups"])
app.include_router(trophies_router.router, prefix="/api/trophy", tags=["trophies"])
app.include_router(exports_router.router, prefix="/api/export", tags=["exports"])
app.include_router(images_router.router, prefix="/api/image", tags=["images"])


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
