from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.api_core import exceptions as google_api_exceptions

from app.api.router import public_router
from app.core.config import settings
from app.exceptions import ServiceUnavailableError
from app.websocket.connection_manager import ConnectionManager
from app.websocket.router import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.connection_manager = ConnectionManager()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)


@app.exception_handler(google_api_exceptions.GoogleAPIError)
async def google_api_error_handler(_request: Request, _exc: google_api_exceptions.GoogleAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable. Please try again."},
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_handler(_request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


app.include_router(public_router)
app.include_router(websocket_router)
