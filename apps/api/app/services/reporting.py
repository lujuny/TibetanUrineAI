from typing import Any

from app.core.safety import SAFETY_NOTE
from app.models.schemas import ObservationRecord


def create_case_report(observation: ObservationRecord, history: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "report_id": f"report_{observation.id}",
        "case_id": observation.case_id,
        "observation_id": observation.id,
        "collection_context": observation.collection_context.model_dump(),
        "image_quality": observation.quality_result,
        "visual_features": observation.visual_features,
        "symptom_profile": observation.symptom_profile,
        "assisted_interpretation": observation.assisted_interpretation,
        "history_comparison": history,
        "doctor_review": None,
        "safety_note": SAFETY_NOTE,
    }

