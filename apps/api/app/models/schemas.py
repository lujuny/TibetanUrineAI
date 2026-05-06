from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CaseCreate(BaseModel):
    age_group: str | None = None
    gender: str | None = None
    notes: str | None = None


class CaseRecord(CaseCreate):
    id: str = Field(default_factory=lambda: f"case_{uuid4().hex[:10]}")
    anonymous_code: str
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CollectionContext(BaseModel):
    lighting_condition: str | None = None
    container_type: str | None = None
    background_type: str | None = None
    resting_minutes: int | None = None
    is_morning_sample: bool | None = None
    interference_note: str | None = None


class SymptomContext(BaseModel):
    chief_complaint: str | None = None
    duration: str | None = None
    sleep: str | None = None
    diet: str | None = None
    water_intake: str | None = None
    urination: str | None = None
    stool: str | None = None
    medication: str | None = None


class ObservationCreate(BaseModel):
    case_id: str
    image_path: str | None = None
    collection_context: CollectionContext = Field(default_factory=CollectionContext)
    symptom_context: SymptomContext = Field(default_factory=SymptomContext)
    symptom_text: str | None = None


class ObservationUpdate(BaseModel):
    case_id: str | None = None
    image_path: str | None = None
    collection_context: CollectionContext | None = None
    symptom_context: SymptomContext | None = None
    symptom_text: str | None = None


class ObservationRecord(ObservationCreate):
    id: str = Field(default_factory=lambda: f"obs_{uuid4().hex[:10]}")
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    quality_result: dict[str, Any] | None = None
    visual_features: dict[str, Any] | None = None
    symptom_profile: dict[str, Any] | None = None
    assisted_interpretation: dict[str, Any] | None = None
    report: dict[str, Any] | None = None


class ImageUploadResponse(BaseModel):
    image_id: str
    filename: str
    content_type: str
    image_path: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
