from typing import Any

from app.core.safety import SAFETY_NOTE


def generate_assisted_interpretation(
    *,
    quality_result: dict[str, Any] | None,
    visual_features: dict[str, Any] | None,
    symptom_profile: dict[str, Any] | None,
    history: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "observation_summary": "系统已完成图像质量、视觉特征和症状信息的初步整理。",
        "candidate_interpretations": [
            {
                "title": "需由专业藏医师复核的候选观察",
                "confidence": "medium",
                "evidence": [
                    "图像质量结果已生成",
                    "视觉特征结果已生成",
                    "症状信息已结构化",
                ],
                "uncertainties": [
                    "当前 Agent 为占位实现，尚未接入真实 Gemma 4 调用。",
                ],
                "follow_up_questions": [
                    "近期是否服用药物或保健品？",
                    "样本静置时间是否已记录？",
                ],
            }
        ],
        "inputs": {
            "quality_result": quality_result,
            "visual_features": visual_features,
            "symptom_profile": symptom_profile,
            "history": history,
        },
        "safety_note": SAFETY_NOTE,
    }

