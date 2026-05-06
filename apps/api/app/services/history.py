from typing import Any

from app.models.schemas import ObservationRecord


def compare_history(
    current: ObservationRecord,
    observations: list[ObservationRecord],
) -> dict[str, Any]:
    related = [item for item in observations if item.case_id == current.case_id]
    related.sort(key=lambda item: item.created_at)

    if len(related) <= 1:
        return {
            "available": False,
            "records_compared": len(related),
            "trend_summary": "当前病例暂无足够历史记录进行趋势对比。",
            "notable_changes": [],
        }

    return {
        "available": True,
        "records_compared": len(related),
        "trend_summary": "已找到多次观察记录，后续将接入真实趋势计算。",
        "notable_changes": [],
    }

