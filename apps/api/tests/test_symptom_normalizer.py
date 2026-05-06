from fastapi.testclient import TestClient

from app.main import app
from app.services.symptom_normalizer import normalize_symptoms


def test_normalize_symptoms_extracts_structured_fields() -> None:
    result = normalize_symptoms(
        "患者近三天口干，晚上睡眠差，感觉乏力，最近饮水较少，饮食偏油腻，小便黄，大便干。"
    )

    profile = result["symptom_profile"]

    assert result["status"] == "completed"
    assert profile["duration"] == "三天"
    assert "口干" in profile["symptom_tags"]
    assert "乏力" in profile["symptom_tags"]
    assert profile["sleep"] == "睡眠差"
    assert profile["diet"] == "饮食油腻"
    assert profile["water_intake"] == "饮水少"
    assert profile["urination"] == "尿黄"
    assert profile["stool"] == "大便干"
    assert "近期用药情况" in result["missing_fields"]
    assert result["follow_up_questions"]


def test_normalize_symptoms_detects_interference_factors() -> None:
    result = normalize_symptoms("最近吃了维生素和中药，喝水少，尿黄，睡眠一般。")
    profile = result["symptom_profile"]

    assert profile["medication"] == "已提及"
    assert "近期用药情况" not in result["missing_fields"]
    assert {item["label"] for item in profile["interference_factors"]} >= {
        "近期用药",
        "保健品或维生素",
    }


def test_normalize_symptoms_distinguishes_negated_medication() -> None:
    result = normalize_symptoms("近2天口干，睡眠一般，饮水少，饮食清淡，小便黄，大便干，没有吃药。")
    profile = result["symptom_profile"]

    assert profile["medication"] == "否认近期用药/保健品"
    assert "近期用药情况" not in result["missing_fields"]
    assert "否认近期用药" in {item["label"] for item in profile["interference_factors"]}


def test_normalize_symptoms_empty_text_requests_core_fields() -> None:
    result = normalize_symptoms(None)

    assert result["status"] == "skipped"
    assert result["symptom_profile"]["chief_complaint"] == "未提供"
    assert "主诉" in result["missing_fields"]
    assert result["confidence"] == "low"


def test_normalize_symptoms_uses_structured_context_fields() -> None:
    result = normalize_symptoms(
        "尿色偏黄。",
        symptom_context={
            "chief_complaint": "尿黄",
            "duration": "4天",
            "sleep": "睡眠一般",
            "diet": "偏油腻",
            "water_intake": "饮水少",
            "urination": "尿黄",
            "stool": "大便正常",
            "medication": "未服药",
        },
    )
    profile = result["symptom_profile"]

    assert profile["chief_complaint"] == "尿黄"
    assert profile["duration"] == "4天"
    assert profile["sleep"] == "睡眠一般"
    assert profile["diet"] == "偏油腻"
    assert profile["water_intake"] == "饮水少"
    assert profile["medication"] == "未服药"
    assert result["missing_fields"] == []
    assert profile["structured_input"]["duration"] == "4天"


def test_normalize_observation_symptoms_endpoint() -> None:
    client = TestClient(app)
    case = client.post("/api/cases", json={}).json()
    observation = client.post(
        "/api/observations",
        json={
            "case_id": case["id"],
            "image_path": "/tmp/missing.jpg",
            "symptom_context": {
                "duration": "2天",
                "sleep": "睡眠一般",
                "diet": "饮食清淡",
                "water_intake": "饮水少",
                "stool": "大便正常",
                "medication": "未服药",
            },
            "symptom_text": "近2天口干乏力，饮水少，小便黄。",
        },
    ).json()

    response = client.post(f"/api/observations/{observation['id']}/symptoms")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symptom_profile"]["status"] == "completed"
    assert payload["symptom_profile"]["symptom_profile"]["duration"] == "2天"
    assert payload["symptom_context"]["sleep"] == "睡眠一般"
    assert "口干" in payload["symptom_profile"]["symptom_profile"]["symptom_tags"]
