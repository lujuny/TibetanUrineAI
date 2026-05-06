from pathlib import Path

from PIL import Image, ImageDraw

from app.core.config import get_settings
from app.services.image_quality import assess_image_quality


def test_assess_image_quality_reads_uploaded_file(tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    upload_dir = tmp_path / "uploads"
    sample_dir = upload_dir / "20260506"
    sample_dir.mkdir(parents=True)
    sample_path = sample_dir / "sample.png"

    image = Image.new("RGB", (800, 800), (198, 202, 196))
    draw = ImageDraw.Draw(image)
    draw.ellipse((180, 180, 620, 620), fill=(190, 132, 35), outline=(82, 64, 38), width=8)
    draw.line((180, 400, 620, 400), fill=(126, 83, 25), width=5)
    draw.line((400, 180, 400, 620), fill=(126, 83, 25), width=5)
    image.save(sample_path)

    settings.upload_dir = str(upload_dir)

    try:
        result = assess_image_quality("/uploads/20260506/sample.png")
    finally:
        settings.upload_dir = original_upload_dir

    assert 0 <= result["quality_score"] <= 100
    assert isinstance(result["usable"], bool)
    assert result["metrics"]["width"] == 800
    assert result["metrics"]["height"] == 800


def test_assess_image_quality_rejects_invalid_image(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.png"
    invalid_path.write_text("not an image", encoding="utf-8")

    result = assess_image_quality(str(invalid_path))

    assert result["quality_score"] == 0
    assert result["usable"] is False
    assert result["issues"][0]["type"] == "invalid_image"


def test_assess_image_quality_fuses_gemma_review(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "sample.png"
    image = Image.new("RGB", (800, 800), (210, 205, 195))
    draw = ImageDraw.Draw(image)
    draw.ellipse((160, 160, 640, 640), fill=(192, 132, 38), outline=(86, 65, 35), width=8)
    image.save(image_path)

    def fake_gemma_review(*, image_file: Path, rule_result: dict):
        return {
            "status": "completed",
            "provider": "gemma4",
            "sample_visible": True,
            "urine_region_complete": True,
            "sample_region_size": "small",
            "background": "white_or_light",
            "reflection_risk": "mild",
            "blur_risk": "none",
            "collection_quality": "acceptable",
            "confidence": "high",
            "issues": [
                {
                    "type": "sample_region_small",
                    "severity": "medium",
                    "message": "Gemma4 认为尿液样本区域略小。",
                    "source": "gemma4",
                }
            ],
            "recommendations": ["建议靠近容器重新拍摄。"],
        }

    monkeypatch.setattr(
        "app.services.image_quality.review_image_quality_with_gemma",
        fake_gemma_review,
    )

    result = assess_image_quality(str(image_path))

    assert result["gemma_review"]["status"] == "completed"
    assert result["score_sources"]["fusion_method"] == "rule_cv_score_minus_gemma_penalty"
    assert result["score_sources"]["gemma_penalty"] > 0
    assert any(issue.get("source") == "gemma4" for issue in result["issues"])
