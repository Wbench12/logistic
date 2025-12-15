from fastapi import APIRouter

from app.api.routes import login, private, users, utils, company, trip
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(company.router_companies)
api_router.include_router(company.router_vehicles)
api_router.include_router(trip.router_trips)
# api_router.include_router(optimization.router, prefix="/v1")

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)

# Add health check endpoint
@api_router.get("/health")
def health_check():
    return {"status": "healthy", "service": "logistics-platform"}

# Add version info
@api_router.get("/version")
def version_info():
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "features": [
            "trip_management",
            "cross_company_optimization",
            "map_visualization",
            "kpi_tracking",
            "trip_upload"
        ]
    }