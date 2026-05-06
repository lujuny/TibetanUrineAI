from fastapi import APIRouter, HTTPException

from app.db.session import store
from app.models.schemas import ObservationCreate, ObservationRecord, ObservationUpdate
from app.services.agent import generate_assisted_interpretation
from app.services.feature_extraction import extract_visual_features
from app.services.history import compare_history
from app.services.image_quality import assess_image_quality
from app.services.reporting import create_case_report
from app.services.symptom_normalizer import normalize_symptoms

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("", response_model=ObservationRecord)
def create_observation(payload: ObservationCreate) -> ObservationRecord:
    if store.get_case(payload.case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    observation = ObservationRecord(**payload.model_dump())
    observation.quality_result = assess_image_quality(observation.image_path)
    return store.create_observation(observation)


@router.get("/{observation_id}", response_model=ObservationRecord)
def get_observation(observation_id: str) -> ObservationRecord:
    observation = store.get_observation(observation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    return observation


@router.patch("/{observation_id}", response_model=ObservationRecord)
def update_observation(
    observation_id: str,
    payload: ObservationUpdate,
) -> ObservationRecord:
    observation = get_observation(observation_id)
    updated_fields = payload.model_fields_set

    if not updated_fields:
        return observation

    if "case_id" in updated_fields:
        if not payload.case_id:
            raise HTTPException(status_code=422, detail="Case id is required")
        if store.get_case(payload.case_id) is None:
            raise HTTPException(status_code=404, detail="Case not found")
        observation.case_id = payload.case_id

    if "image_path" in updated_fields:
        observation.image_path = payload.image_path

    if "collection_context" in updated_fields and payload.collection_context is not None:
        observation.collection_context = payload.collection_context

    if "symptom_context" in updated_fields and payload.symptom_context is not None:
        observation.symptom_context = payload.symptom_context

    if "symptom_text" in updated_fields:
        observation.symptom_text = payload.symptom_text

    observation.quality_result = assess_image_quality(observation.image_path)
    observation.visual_features = None
    observation.symptom_profile = None
    observation.assisted_interpretation = None
    observation.report = None

    return store.save_observation(observation)


@router.post("/{observation_id}/quality", response_model=ObservationRecord)
def assess_observation_quality(observation_id: str) -> ObservationRecord:
    observation = get_observation(observation_id)
    observation.quality_result = assess_image_quality(observation.image_path)
    return store.save_observation(observation)


@router.post("/{observation_id}/features", response_model=ObservationRecord)
def extract_observation_features(observation_id: str) -> ObservationRecord:
    observation = get_observation(observation_id)
    observation.visual_features = extract_visual_features(observation.image_path)
    observation.assisted_interpretation = None
    observation.report = None
    return store.save_observation(observation)


@router.post("/{observation_id}/symptoms", response_model=ObservationRecord)
def normalize_observation_symptoms(observation_id: str) -> ObservationRecord:
    observation = get_observation(observation_id)
    observation.symptom_profile = normalize_symptoms(
        observation.symptom_text,
        symptom_context=observation.symptom_context.model_dump(mode="json"),
    )
    observation.assisted_interpretation = None
    observation.report = None
    return store.save_observation(observation)


@router.post("/{observation_id}/analyze", response_model=ObservationRecord)
def analyze_observation(observation_id: str) -> ObservationRecord:
    observation = get_observation(observation_id)
    observation.quality_result = assess_image_quality(observation.image_path)
    observation.visual_features = extract_visual_features(observation.image_path)
    observation.symptom_profile = normalize_symptoms(
        observation.symptom_text,
        symptom_context=observation.symptom_context.model_dump(mode="json"),
    )
    history = compare_history(observation, store.list_observations())
    observation.assisted_interpretation = generate_assisted_interpretation(
        quality_result=observation.quality_result,
        visual_features=observation.visual_features,
        symptom_profile=observation.symptom_profile,
        history=history,
    )
    observation.report = create_case_report(observation, history)
    return store.save_observation(observation)
