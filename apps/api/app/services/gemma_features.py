import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.gemma_client import send_gemma_vision_chat


FEATURE_KEYS = ("color", "transparency", "foam", "sediment", "layering")


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


def _normalize_foam_label(label: str, evidence: str) -> str:
    if label != "未见明显泡沫":
        return label

    absence_markers = (
        "未观察到",
        "未见任何",
        "完全没有",
        "无气泡",
        "无泡沫",
    )
    subtle_foam_markers = (
        "极少量",
        "少量",
        "细微气泡",
        "小气泡",
        "零散",
        "离散",
        "边缘",
        "泡沫点",
    )
    if (
        any(marker in evidence for marker in subtle_foam_markers)
        and not any(marker in evidence for marker in absence_markers)
    ):
        return "少量泡沫"

    return label


def _normalize_feature(value: Any, *, key: str | None = None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    label = str(value.get("label") or "").strip()
    if not label:
        return None

    try:
        confidence = float(value.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6

    confidence = max(0.0, min(1.0, confidence))
    evidence = str(value.get("evidence") or "").strip()
    if key == "foam":
        label = _normalize_foam_label(label, evidence)

    return {
        "label": label,
        "confidence": round(confidence, 2),
        "evidence": evidence or "Gemma4 基于图像进行多模态复核。",
        "source": "gemma4",
    }


def review_visual_features_with_gemma(
    *,
    image_file: Path,
    rule_result: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.gemma_feature_review_enabled:
        return {
            "status": "skipped",
            "provider": "gemma4",
            "reason": "Gemma4 feature review is disabled.",
        }

    if not settings.gemma_api_base:
        return {
            "status": "skipped",
            "provider": "gemma4",
            "reason": "GEMMA_API_BASE is not configured.",
        }

    prompt = f"""
你是藏医尿诊智能辅助系统的尿液图像视觉特征复核助手。
你的任务不是医学诊断，也不要判断疾病或给治疗建议，只提取图像中可观察的视觉特征。

规则/CV初步结果只作为参考，可能存在误判，不要直接复述规则/CV标签。
如果图片本身与规则/CV初步结果不一致，请以图片本身为准。

尤其注意 foam（泡沫）：
- 不要把容器边缘反光、白色背景、尿液表面亮斑、杯壁边缘高亮判断为泡沫。
- 只有尿液表面存在明确、成簇、连续的白色气泡或泡沫点，才判断为“较多泡沫”。
- 如果尿液表面或液面边缘存在少量、极少量、零散的白色气泡/泡沫点，应判断为“少量泡沫”。
- 只有未观察到可辨认的气泡或泡沫点时，才判断为“未见明显泡沫”。
- 如果只是杯壁反光、白色背景、液面亮斑且没有圆点状/颗粒状气泡形态，应判断为“未见明显泡沫”。
- foam 的 evidence 必须描述你在图片中实际看到的泡沫位置和形态，不要使用“高亮低饱和区域占比”等规则指标作为证据。

请结合图片本身和以下规则/CV初步结果进行复核：
{json.dumps(rule_result.get("features", {}), ensure_ascii=False)}

请输出以下五类视觉特征：
1. color：颜色，例如淡黄色、黄色、深黄色、橙黄色、棕黄色
2. transparency：透明度，例如清亮、轻度浑浊、明显浑浊
3. foam：泡沫，例如未见明显泡沫、少量泡沫、较多泡沫
4. sediment：沉淀，例如未见明显沉淀、少量沉淀、明显沉淀
5. layering：分层，例如未见明显分层、疑似分层、明显分层

只返回一个 JSON 对象，不要输出 Markdown，不要输出解释性前后缀。格式如下：
{{
  "features": {{
    "color": {{"label": "深黄色", "confidence": 0.75, "evidence": "尿液主体呈较深黄色。"}},
    "transparency": {{"label": "轻度浑浊", "confidence": 0.65, "evidence": "样本边界清楚但内部略不均匀。"}},
    "foam": {{"label": "少量泡沫", "confidence": 0.7, "evidence": "表面可见少量白色泡沫。"}},
    "sediment": {{"label": "未见明显沉淀", "confidence": 0.6, "evidence": "底部未见清晰沉积区域。"}},
    "layering": {{"label": "未见明显分层", "confidence": 0.7, "evidence": "整体颜色层次连续。"}}
  }},
  "summary": "图像中尿液主体偏深黄色，可见少量泡沫。",
  "recommendations": ["建议结合采集条件和专业复核确认。"]
}}
""".strip()

    response = send_gemma_vision_chat(
        system_prompt="你只负责尿液图像视觉特征提取，不提供医学诊断或治疗建议。",
        user_prompt=prompt,
        image_file=image_file,
        timeout_seconds=settings.gemma_feature_timeout_seconds,
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

    raw_features = parsed.get("features", {})
    features: dict[str, Any] = {}
    if isinstance(raw_features, dict):
        for key in FEATURE_KEYS:
            normalized = _normalize_feature(raw_features.get(key), key=key)
            if normalized:
                features[key] = normalized

    recommendations = [
        str(item).strip()
        for item in parsed.get("recommendations", [])
        if str(item).strip()
    ]

    return {
        "status": "completed",
        "provider": "gemma4",
        "provider_api": response.get("provider_api", "unknown"),
        "features": features,
        "summary": str(parsed.get("summary") or "").strip(),
        "recommendations": recommendations,
        "raw_excerpt": str(message)[:500],
    }
