"""Model shortcuts for the FastAPI app."""

from .user_models import (  # noqa: F401
    User,
    UserCreate,
    UserUpdate,
    UserUpdateMe,
    UserPublic,
    UsersPublic,
    UserRegister,
    UpdatePassword,
    NewPassword,
    Token,
    TokenPayload,
)
from .company_models import (
    Company,
    CompanyCreate,
    CompanyPublic,
    CompanyUpdate,
    Vehicle,
    VehicleCreate,
    VehicleUpdate,
    VehiclePublic,
    VehiclesPublic,
)  # noqa: F401
from .trip_models import (
    Trip,
    TripCreate,
    TripPublic,
    TripsPublic,
    TripUpdate,
    TripStatus,
    DashboardMetrics,
    OptimizationBatch,
    OptimizationBatchPublic,
)  # noqa: F401
from .user_models import Message  # noqa: F401
