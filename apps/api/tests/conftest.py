from pathlib import Path

import pytest

from app.core.config import get_settings
from app.db.session import store


@pytest.fixture(autouse=True)
def isolated_sqlite_store(tmp_path: Path):
    settings = get_settings()
    original_gemma_quality_review_enabled = settings.gemma_quality_review_enabled
    original_gemma_feature_review_enabled = settings.gemma_feature_review_enabled
    settings.gemma_quality_review_enabled = False
    settings.gemma_feature_review_enabled = False
    store.configure(f"sqlite:///{tmp_path / 'test.db'}")
    yield
    store.clear_all()
    settings.gemma_quality_review_enabled = original_gemma_quality_review_enabled
    settings.gemma_feature_review_enabled = original_gemma_feature_review_enabled
