"""FastAPI dependencies for the active FHIR/PDF demo workflow."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request

from src.clinical.access import AuthProvider
from src.clinical.audit import AuditSink, CompositeAuditSink, StructuredAuditSink
from src.clinical.demo_auth import DemoSessionProvider
from src.clinical.demo_repository import DemoRepository
from src.clinical.operations import OperationalStore, operational_store
from src.clinical.schemas import AccessContext
from src.config import get_settings

_PATIENT_SCOPE_DENIED = {
    "code": "PATIENT_SCOPE_DENIED",
    "message": "Bệnh nhân không tồn tại hoặc không có quyền truy cập.",
}


def require_patient(repo: DemoRepository, patient_id: str):
    """Validate patient exists and return it, or raise 404."""
    patient = repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=_PATIENT_SCOPE_DENIED)
    return patient


def get_audit_sink() -> AuditSink:
    return CompositeAuditSink(operational_store, StructuredAuditSink())


def get_operational_store() -> OperationalStore:
    return operational_store


def get_access_context(request: Request) -> AccessContext:
    request.state.clinical_trace_id = str(uuid4())
    provider: AuthProvider = DemoSessionProvider()
    return provider.authenticate(request)


_demo_repo_instance: DemoRepository | None = None


def get_demo_repository() -> DemoRepository:
    global _demo_repo_instance
    if _demo_repo_instance is None:
        state_path = Path(get_settings().demo_data_dir) / ".runtime" / "review_state.json"
        _demo_repo_instance = DemoRepository(state_path=state_path)
    return _demo_repo_instance

