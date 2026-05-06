from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.db.session import store
from app.models.schemas import CaseCreate, CaseRecord, ObservationRecord

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseRecord)
def create_case(payload: CaseCreate) -> CaseRecord:
    date_prefix = datetime.now().strftime("%Y%m%d")
    serial = store.next_case_serial(date_prefix)
    anonymous_code = f"TM-{date_prefix}-{serial:03d}"
    case = CaseRecord(**payload.model_dump(), anonymous_code=anonymous_code)
    return store.create_case(case)


@router.get("", response_model=list[CaseRecord])
def list_cases() -> list[CaseRecord]:
    return store.list_cases()


@router.get("/{case_id}", response_model=CaseRecord)
def get_case(case_id: str) -> CaseRecord:
    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/{case_id}/observations", response_model=list[ObservationRecord])
def list_case_observations(case_id: str) -> list[ObservationRecord]:
    if store.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return store.list_case_observations(case_id)
