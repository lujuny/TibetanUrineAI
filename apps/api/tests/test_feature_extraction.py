from pathlib import Path

from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.main import app
from app.services.feature_extraction import extract_visual_features


def _sample_urine_image(path: Path) -> None:
    image = Image.new("RGB", (900, 900), (236, 236, 230))
    draw = ImageDraw.Draw(image)
    draw.ellipse((190, 190, 710, 710), fill=(190, 132, 38), outline=(92, 66, 34), width=8)
    draw.ellipse((360, 245, 500, 300), fill=(248, 248, 238))
    draw.rectangle((280, 610, 610, 650), fill=(112, 75, 30))
    image.save(path)


def _sample_reflective_urine_image(path: Path) -> None:
    image = Image.new("RGB", (900, 900), (245, 245, 240))
    draw = ImageDraw.Draw(image)
    draw.ellipse((230, 190, 670, 690), fill=(203, 156, 48), outline=(210, 210, 198), width=12)
    draw.arc((235, 195, 665, 685), start=200, end=340, fill=(255, 255, 245), width=14)
    draw.ellipse((610, 520, 625, 535), fill=(252, 252, 246))
    image.save(path)


def test_extract_visual_features_rule_cv(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    _sample_urine_image(image_path)

    result = extract_visual_features(str(image_path), include_gemma=False)

    assert result["status"] == "completed"
    assert result["features"]["color"]["label"]
    assert result["features"]["transparency"]["label"]
    assert result["features"]["foam"]["label"]
    assert result["features"]["sediment"]["label"]
    assert result["features"]["layering"]["label"]
    assert result["gemma_review"]["status"] == "skipped"


def test_reflective_edges_do_not_become_heavy_foam(tmp_path: Path) -> None:
    image_path = tmp_path / "reflective.png"
    _sample_reflective_urine_image(image_path)

    result = extract_visual_features(str(image_path), include_gemma=False)

    assert result["status"] == "completed"
    assert result["features"]["foam"]["label"] != "较多泡沫"
    metrics = result["features"]["foam"]["metrics"]
    assert "foam_candidate_ratio" in metrics
    assert "ignored_bright_region_ratio" in metrics


def test_extract_visual_features_fuses_gemma_review(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    _sample_urine_image(image_path)

    def fake_gemma_review(*, image_file: Path, rule_result: dict):
        return {
            "status": "completed",
            "provider": "gemma4",
            "features": {
                "color": {
                    "label": "深黄色",
                    "confidence": 0.82,
                    "evidence": "Gemma4 观察到主体色彩偏深。",
                    "source": "gemma4",
                },
                "foam": {
                    "label": "少量泡沫",
                    "confidence": 0.75,
                    "evidence": "Gemma4 观察到表面白色泡沫。",
                    "source": "gemma4",
                },
            },
            "summary": "Gemma4 复核认为颜色偏深并有少量泡沫。",
            "recommendations": ["建议结合采集条件复核。"],
        }

    monkeypatch.setattr(
        "app.services.feature_extraction.review_visual_features_with_gemma",
        fake_gemma_review,
    )

    result = extract_visual_features(str(image_path))

    assert result["gemma_review"]["status"] == "completed"
    assert result["features"]["color"]["label"] == "深黄色"
    assert result["features"]["color"]["source"] == "rule_cv+gemma4"
    assert result["features"]["color"]["rule_label"]
    assert result["features"]["color"]["gemma_label"] == "深黄色"


def test_generic_gemma_foam_evidence_does_not_upgrade_label(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "reflective.png"
    _sample_reflective_urine_image(image_path)

    def fake_gemma_review(*, image_file: Path, rule_result: dict):
        return {
            "status": "completed",
            "provider": "gemma4",
            "features": {
                "foam": {
                    "label": "较多泡沫",
                    "confidence": 0.8,
                    "evidence": "基于高亮低饱和区域占比粗略估算泡沫较多。",
                    "source": "gemma4",
                },
            },
            "summary": "Gemma4 复核认为泡沫较多。",
            "recommendations": [],
        }

    monkeypatch.setattr(
        "app.services.feature_extraction.review_visual_features_with_gemma",
        fake_gemma_review,
    )

    result = extract_visual_features(str(image_path))

    assert result["gemma_review"]["status"] == "completed"
    assert result["features"]["foam"]["label"] != "较多泡沫"
    assert result["features"]["foam"]["source"] == "rule_cv_conservative"
    assert result["features"]["foam"]["gemma_label"] == "较多泡沫"


def test_subtle_edge_bubbles_are_fused_as_light_foam(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    _sample_reflective_urine_image(image_path)

    def fake_gemma_review(*, image_file: Path, rule_result: dict):
        return {
            "status": "completed",
            "provider": "gemma4",
            "features": {
                "foam": {
                    "label": "少量泡沫",
                    "confidence": 0.8,
                    "evidence": "尿液表面边缘区域可见少量离散的白色泡沫点。",
                    "source": "gemma4",
                },
            },
            "summary": "Gemma4 复核认为边缘有少量泡沫。",
            "recommendations": [],
        }

    monkeypatch.setattr(
        "app.services.feature_extraction.review_visual_features_with_gemma",
        fake_gemma_review,
    )

    result = extract_visual_features(str(image_path))

    assert result["features"]["foam"]["label"] == "少量泡沫"
    assert result["features"]["foam"]["source"] == "rule_cv+gemma4"


def test_extract_observation_features_endpoint() -> None:
    client = TestClient(app)
    case = client.post("/api/cases", json={}).json()
    observation = client.post(
        "/api/observations",
        json={"case_id": case["id"], "image_path": "/tmp/missing.jpg"},
    ).json()

    response = client.post(f"/api/observations/{observation['id']}/features")

    assert response.status_code == 200
    payload = response.json()
    assert payload["visual_features"]["status"] == "failed"
    assert payload["visual_features"]["recommendations"]
