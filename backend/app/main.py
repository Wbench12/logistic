import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.main import api_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


def format_validation_error(error: ValidationError | RequestValidationError) -> dict:
    """Format Pydantic validation errors into user-friendly French messages"""
    errors = []
    
    field_names = {
        "company_name": "Nom de l'entreprise",
        "nis": "NIS",
        "nif": "NIF",
        "headquarters_address": "Adresse du siège",
        "company_type": "Type d'entreprise",
        "activity_sector": "Secteur d'activité",
        "partner_type": "Type de partenaire",
        "legal_representative_name": "Nom du représentant légal",
        "legal_representative_contact": "Contact du représentant",
    }
    
    for err in error.errors():
        field = err.get("loc", [""])[-1]  # Get last element of location path
        field_display = field_names.get(field, field)
        error_type = err.get("type", "")
        
        # Customize messages based on error type
        if "string_pattern_mismatch" in error_type:
            if field == "nis":
                msg = f"{field_display}: Doit contenir uniquement des chiffres (maximum 15)"
            elif field == "nif":
                msg = f"{field_display}: Doit contenir entre 15 et 20 chiffres uniquement"
            elif field == "legal_representative_contact":
                msg = f"{field_display}: Format invalide. Utilisez +213XXXXXXXXX"
            else:
                msg = f"{field_display}: Format invalide"
        elif "string_too_short" in error_type:
            msg = f"{field_display}: Trop court (minimum {err.get('ctx', {}).get('min_length', '')} caractères)"
        elif "string_too_long" in error_type:
            msg = f"{field_display}: Trop long (maximum {err.get('ctx', {}).get('max_length', '')} caractères)"
        elif "missing" in error_type:
            msg = f"{field_display}: Champ obligatoire"
        elif "enum" in error_type:
            msg = f"{field_display}: Valeur non valide"
        else:
            msg = err.get("msg", f"{field_display}: Erreur de validation")
        
        errors.append(msg)
    
    return {
        "detail": " | ".join(errors) if errors else "Erreur de validation des données",
        "errors": errors
    }


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with user-friendly messages"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_validation_error(exc),
    )

# Set all CORS enabled origins
if settings.all_cors_origins:
    allow_origins = settings.all_cors_origins
    allow_credentials = True

    if settings.ENVIRONMENT == "local":
        allow_origins = ["*"]
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
