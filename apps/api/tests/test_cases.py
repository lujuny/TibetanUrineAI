from fastapi.testclient import TestClient

from app.db.session import store
from app.main import app


def test_create_and_list_cases() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/cases",
        json={"age_group": "30-40", "gender": "female", "notes": "演示病例"},
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["anonymous_code"].startswith("TM-")
    assert created["age_group"] == "30-40"

    list_response = client.get("/api/cases")

    assert list_response.status_code == 200
    cases = list_response.json()
    assert len(cases) == 1
    assert cases[0]["id"] == created["id"]


def test_cases_persist_after_store_reconfigure() -> None:
    client = TestClient(app)
    database_url = store.database_url

    created = client.post("/api/cases", json={"notes": "持久化验证"}).json()

    store.configure(database_url)
    list_response = client.get("/api/cases")

    assert list_response.status_code == 200
    cases = list_response.json()
    assert len(cases) == 1
    assert cases[0]["id"] == created["id"]
    assert cases[0]["notes"] == "持久化验证"


def test_list_case_observations() -> None:
    client = TestClient(app)
    case = client.post("/api/cases", json={}).json()

    observation_response = client.post(
        "/api/observations",
        json={"case_id": case["id"], "image_path": "/tmp/demo.jpg"},
    )

    assert observation_response.status_code == 200
    observation = observation_response.json()
    assert observation["quality_result"]["usable"] is False
    assert observation["quality_result"]["issues"][0]["type"] == "file_not_found"

    observations_response = client.get(f"/api/cases/{case['id']}/observations")

    assert observations_response.status_code == 200
    observations = observations_response.json()
    assert len(observations) == 1
    assert observations[0]["case_id"] == case["id"]


def test_update_observation() -> None:
    client = TestClient(app)
    case = client.post("/api/cases", json={}).json()

    created = client.post(
        "/api/observations",
        json={
            "case_id": case["id"],
            "image_path": "/uploads/old.jpg",
            "collection_context": {"lighting_condition": "自然光"},
            "symptom_context": {"duration": "1天", "sleep": "睡眠差"},
            "symptom_text": "原始备注",
        },
    ).json()

    response = client.patch(
        f"/api/observations/{created['id']}",
        json={
            "image_path": "/uploads/new.jpg",
            "collection_context": {
                "lighting_condition": "室内白光",
                "container_type": "透明杯",
                "resting_minutes": 8,
                "is_morning_sample": True,
            },
            "symptom_context": {
                "duration": "3天",
                "sleep": "睡眠一般",
                "diet": "偏油腻",
                "water_intake": "饮水少",
            },
            "symptom_text": "修改后的备注",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == created["id"]
    assert updated["case_id"] == case["id"]
    assert updated["image_path"] == "/uploads/new.jpg"
    assert updated["collection_context"]["lighting_condition"] == "室内白光"
    assert updated["collection_context"]["container_type"] == "透明杯"
    assert updated["collection_context"]["resting_minutes"] == 8
    assert updated["collection_context"]["is_morning_sample"] is True
    assert updated["symptom_context"]["duration"] == "3天"
    assert updated["symptom_context"]["sleep"] == "睡眠一般"
    assert updated["symptom_context"]["water_intake"] == "饮水少"
    assert updated["symptom_text"] == "修改后的备注"
    assert updated["quality_result"]["issues"][0]["type"] == "file_not_found"


def test_assess_observation_quality_endpoint() -> None:
    client = TestClient(app)
    case = client.post("/api/cases", json={}).json()
    observation = client.post(
        "/api/observations",
        json={"case_id": case["id"], "image_path": "/tmp/missing.jpg"},
    ).json()

    response = client.post(f"/api/observations/{observation['id']}/quality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["quality_result"]["quality_score"] == 0
    assert payload["quality_result"]["usable"] is False
    assert payload["quality_result"]["recommendations"]


def test_list_case_observations_404() -> None:
    client = TestClient(app)

    response = client.get("/api/cases/missing/observations")

    assert response.status_code == 404
