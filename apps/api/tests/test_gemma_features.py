from app.services.gemma_features import _normalize_feature


def test_foam_normalization_keeps_subtle_bubbles_visible() -> None:
    feature = _normalize_feature(
        {
            "label": "未见明显泡沫",
            "confidence": 0.8,
            "evidence": "尿液表面无成簇、连续的大面积白色泡沫，仅有极少量细微气泡。",
        },
        key="foam",
    )

    assert feature is not None
    assert feature["label"] == "少量泡沫"
