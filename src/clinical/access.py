"""Authentication and patient-assignment checks for the FHIR/PDF workflow."""

from collections.abc import Mapping
from typing import Protocol

import jwt
from fastapi import Request

from src.clinical.errors import ClinicalAccessDenied, ClinicalAuthNotConfigured
from src.clinical.schemas import AccessContext
from src.config import get_settings


class AuthProvider(Protocol):
    def authenticate(self, request: Request) -> AccessContext: ...


class AssignmentProvider(Protocol):
    def can_access(self, context: AccessContext, patient_id: str) -> bool: ...

    def assert_access(self, context: AccessContext, patient_id: str) -> None: ...


class ConfiguredAuthProvider:
    """Validate a production bearer token created by the configured identity layer."""

    def authenticate(self, request: Request) -> AccessContext:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ClinicalAccessDenied("Missing or invalid Authorization header")
        try:
            payload = jwt.decode(
                auth_header.removeprefix("Bearer "),
                get_settings().session_secret,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError as error:
            raise ClinicalAccessDenied("Token has expired") from error
        except jwt.PyJWTError as error:
            raise ClinicalAccessDenied("Invalid token") from error

        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id or not role:
            raise ClinicalAccessDenied("Invalid token payload")
        return AccessContext(
            user_id=str(user_id),
            role=role,
            assigned_patient_ids={str(value) for value in payload.get("assigned_patient_ids", [])},
            trace_id=getattr(request.state, "clinical_trace_id", ""),
        )

