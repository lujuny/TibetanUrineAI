from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.models.schemas import ImageUploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@router.post("", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only jpeg, png, and webp images are supported")

    settings = get_settings()
    date_dir = datetime.now().strftime("%Y%m%d")
    upload_root = Path(settings.upload_dir)
    target_dir = upload_root / date_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    image_id = f"img_{uuid4().hex[:12]}"
    suffix = ALLOWED_IMAGE_TYPES[file.content_type]
    filename = f"{image_id}{suffix}"
    target_path = target_dir / filename

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    target_path.write_bytes(content)

    return ImageUploadResponse(
        image_id=image_id,
        filename=filename,
        content_type=file.content_type,
        image_path=f"/uploads/{date_dir}/{filename}",
    )
