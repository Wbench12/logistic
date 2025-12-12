from fastapi import APIRouter

from app.api.routes import login, private, users, utils, optimization, company, trip
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(company.router_companies)
api_router.include_router(trip.router_trips)
# api_router.include_router(optimization.router, prefix="/v1")

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)