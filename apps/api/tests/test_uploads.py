from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_upload_image(tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path / "uploads")
    client = TestClient(app)

    try:
        response = client.post(
            "/api/uploads",
            files={"file": ("sample.png", b"fake-image-bytes", "image/png")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["image_id"].startswith("img_")
        assert payload["image_path"].startswith("/uploads/")
        assert (tmp_path / "uploads").exists()
    finally:
        settings.upload_dir = original_upload_dir


def test_upload_rejects_non_image(tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path / "uploads")
    client = TestClient(app)

    try:
        response = client.post(
            "/api/uploads",
            files={"file": ("sample.txt", b"not an image", "text/plain")},
        )

        assert response.status_code == 400
    finally:
        settings.upload_dir = original_upload_dir
