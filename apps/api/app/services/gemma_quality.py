import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.gemma_client import send_gemma_vision_chat


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_issue(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None

    issue_type = str(value.get("type") or "gemma_quality_issue")
    severity = str(value.get("severity") or "medium")
    if severity not in {"low", "medium", "high"}:
        severity = "medium"
    message = str(value.get("message") or "").strip()
    if not message:
        return None

    return {
        "type": issue_type,
        "severity": severity,
        "message": message,
        "source": "gemma4",
    }


def _normalize_review(parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
    issues = [
        issue
        for issue in (_normalize_issue(item) for item in parsed.get("issues", []))
        if issue is not None
    ]
    recommendations = [
        str(item).strip()
        for item in parsed.get("recommendations", [])
        if str(item).strip()
    ]

    confidence = str(parsed.get("confidence") or "medium")
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    collection_quality = str(parsed.get("collection_quality") or "unknown")
    if collection_quality not in {"good", "acceptable", "poor", "unknown"}:
        collection_quality = "unknown"

    return {
        "status": "completed",
        "provider": "gemma4",
        "sample_visible": bool(parsed.get("sample_visible", False)),
        "urine_region_complete": bool(parsed.get("urine_region_complete", False)),
        "sample_region_size": str(parsed.get("sample_region_size") or "unknown"),
        "background": str(parsed.get("background") or "unknown"),
        "reflection_risk": str(parsed.get("reflection_risk") or "unknown"),
        "blur_risk": str(parsed.get("blur_risk") or "unknown"),
        "collection_quality": collection_quality,
        "confidence": confidence,
        "issues": issues,
        "recommendations": recommendations,
        "raw_excerpt": raw_text[:500],
    }


def review_image_quality_with_gemma(
    *,
    image_file: Path,
    rule_result: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.gemma_quality_review_enabled:
        return {
            "status": "skipped",
            "provider": "gemma4",
            "reason": "Gemma4 quality review is disabled.",
        }

    if not settings.gemma_api_base:
        return {
            "status": "skipped",
            "provider": "gemma4",
            "reason": "GEMMA_API_BASE is not configured.",
        }

    prompt = f"""
你是藏医尿诊智能辅助系统的图像采集质量复核助手。
你的任务不是做医学诊断，也不要判断疾病，只判断这张尿液样本图片是否适合后续视觉特征分析。

请结合图片本身和规则/CV检测指标进行复核：
{json.dumps(rule_result.get("metrics", {}), ensure_ascii=False)}

请重点检查：
1. 尿液样本是否清楚可见
2. 尿液区域是否完整、是否太小或被遮挡
3. 背景是否复杂，是否影响观察
4. 是否存在明显反光、过曝、偏暗或失焦
5. 是否建议重拍

只返回一个 JSON 对象，不要输出 Markdown，不要输出解释性前后缀。格式如下：
{{
  "sample_visible": true,
  "urine_region_complete": true,
  "sample_region_size": "adequate | small | too_small | unknown",
  "background": "white_or_light | complex | dark | unknown",
  "reflection_risk": "none | mild | moderate | severe | unknown",
  "blur_risk": "none | mild | moderate | severe | unknown",
  "collection_quality": "good | acceptable | poor | unknown",
  "confidence": "low | medium | high",
  "issues": [
    {{"type": "sample_too_small", "severity": "medium", "message": "尿液样本在画面中占比偏小。"}}
  ],
  "recommendations": ["请靠近容器并保持白色背景重新拍摄。"]
}}
""".strip()

    response = send_gemma_vision_chat(
        system_prompt="你只负责图像采集质量复核，不提供医学诊断或治疗建议。",
        user_prompt=prompt,
        image_file=image_file,
        timeout_seconds=settings.gemma_quality_timeout_seconds,
    )
    if response["status"] != "completed":
        return {
            "status": "failed",
            "provider": "gemma4",
            "reason": response.get("reason", "Gemma4 request failed."),
        }

    message = str(response.get("content", ""))

    parsed = _extract_json_object(str(message))
    if not parsed:
        return {
            "status": "failed",
            "provider": "gemma4",
            "reason": "Gemma4 response did not contain a JSON object.",
            "raw_excerpt": str(message)[:500],
        }

    review = _normalize_review(parsed, str(message))
    review["provider_api"] = response.get("provider_api", "unknown")
    return review
