import re
from typing import Any

from app.core.safety import SAFETY_NOTE


FIELD_LABELS = {
    "duration": "持续时间",
    "sleep": "睡眠情况",
    "diet": "饮食情况",
    "water_intake": "饮水情况",
    "medication": "近期用药情况",
    "urination": "小便情况",
    "stool": "大便情况",
}

SYMPTOM_CONTEXT_FIELDS = (
    "chief_complaint",
    "duration",
    "sleep",
    "diet",
    "water_intake",
    "urination",
    "stool",
    "medication",
)

CONTEXT_LABELS = {
    "chief_complaint": "主诉",
    "duration": "持续时间",
    "sleep": "睡眠情况",
    "diet": "饮食情况",
    "water_intake": "饮水情况",
    "urination": "小便情况",
    "stool": "大便情况",
    "medication": "用药/干扰",
}

FOLLOW_UP_QUESTIONS = {
    "duration": "这些症状大约持续了多久？",
    "sleep": "近期睡眠质量、入睡和醒后状态如何？",
    "diet": "近期饮食是否偏油腻、辛辣或有明显变化？",
    "water_intake": "近期饮水量和平时相比是偏多、偏少还是正常？",
    "medication": "近期是否服用药物、保健品或可能影响尿色的食物？",
    "urination": "小便次数、尿急尿痛或夜尿情况是否有变化？",
    "stool": "大便是否干结、稀溏或次数改变？",
}

TAG_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("口干", "mouth_thirst", ("口干", "口渴", "咽干")),
    ("乏力", "energy", ("乏力", "疲乏", "疲劳", "没力气", "无力", "困倦")),
    ("睡眠差", "sleep", ("睡眠差", "睡不好", "失眠", "多梦", "易醒", "入睡困难")),
    ("睡眠一般", "sleep", ("睡眠一般", "睡眠尚可", "睡眠还行")),
    ("饮水少", "water_intake", ("饮水少", "喝水少", "水喝得少", "饮水较少")),
    ("饮水多", "water_intake", ("饮水多", "喝水多", "饮水较多")),
    ("饮食油腻", "diet", ("油腻", "肥甘", "荤腥")),
    ("饮食辛辣", "diet", ("辛辣", "辣")),
    ("食欲差", "appetite_digestive", ("食欲差", "胃口差", "纳差", "不想吃")),
    ("腹胀", "appetite_digestive", ("腹胀", "胀气")),
    ("恶心", "appetite_digestive", ("恶心", "想吐", "呕吐")),
    ("尿黄", "urination", ("尿黄", "小便黄", "尿色黄", "尿液黄")),
    ("尿频", "urination", ("尿频", "小便次数多", "夜尿")),
    ("尿急尿痛", "urination", ("尿急", "尿痛", "刺痛")),
    ("尿少", "urination", ("尿少", "小便少", "尿量少")),
    ("大便干", "stool", ("便干", "大便干", "干结", "便秘")),
    ("大便稀", "stool", ("便稀", "大便稀", "腹泻", "拉肚子", "稀溏")),
    ("头晕", "general", ("头晕", "眩晕")),
    ("头痛", "general", ("头痛",)),
    ("发热", "temperature", ("发热", "发烧", "身热")),
    ("畏寒", "temperature", ("怕冷", "畏寒", "发冷")),
    ("出汗异常", "sweating", ("盗汗", "汗多", "出汗多", "自汗")),
    ("腰痛", "pain", ("腰痛", "腰酸")),
    ("腹痛", "pain", ("腹痛", "肚子痛")),
    ("压力大", "emotion", ("压力大", "焦虑", "烦躁", "情绪")),
)

INTERFERENCE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("近期用药", ("药", "抗生素", "中药", "西药", "止痛药")),
    ("保健品或维生素", ("维生素", "保健品", "补剂")),
    ("饮酒", ("饮酒", "喝酒", "酒后")),
    ("可能影响尿色的饮食", ("甜菜", "火龙果", "色素", "浓茶", "咖啡")),
    ("经期相关", ("月经", "经期", "例假")),
)

NEGATION_MARKERS = ("无", "没有", "未见", "不明显", "否认")
SPLIT_PATTERN = re.compile(r"[，,。；;、\n\r]+")
DURATION_PATTERN = re.compile(
    r"(?:近|最近|持续|已经|约|大约|差不多)?\s*"
    r"([一二两三四五六七八九十半\d]+)\s*"
    r"(天|日|周|星期|个月|月|年|小时)"
)


def _segments(text: str) -> list[str]:
    return [segment.strip() for segment in SPLIT_PATTERN.split(text) if segment.strip()]


def _clean_symptom_context(symptom_context: dict[str, Any] | None) -> dict[str, str]:
    if not symptom_context:
        return {}
    return {
        field_name: str(symptom_context.get(field_name) or "").strip()
        for field_name in SYMPTOM_CONTEXT_FIELDS
        if str(symptom_context.get(field_name) or "").strip()
    }


def _context_text(symptom_context: dict[str, str]) -> str:
    return "；".join(
        f"{CONTEXT_LABELS[field_name]}：{value}"
        for field_name, value in symptom_context.items()
    )


def _contains_negated(segment: str, keyword: str) -> bool:
    index = segment.find(keyword)
    if index < 0:
        return False
    prefix = segment[max(0, index - 4) : index]
    return any(marker in prefix for marker in NEGATION_MARKERS)


def _extract_tags(segments: list[str]) -> tuple[list[dict[str, str]], dict[str, list[str]]]:
    mentions: list[dict[str, str]] = []
    grouped: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()

    for segment in segments:
        for label, category, keywords in TAG_PATTERNS:
            matched_keyword = next(
                (
                    keyword
                    for keyword in keywords
                    if keyword in segment and not _contains_negated(segment, keyword)
                ),
                None,
            )
            if not matched_keyword:
                continue

            key = (label, category)
            if key in seen:
                continue
            seen.add(key)
            mentions.append(
                {
                    "label": label,
                    "category": category,
                    "evidence": segment[:80],
                }
            )
            grouped.setdefault(category, []).append(label)

    return mentions, grouped


def _extract_duration(text: str) -> str | None:
    match = DURATION_PATTERN.search(text)
    if not match:
        return None
    return f"{match.group(1)}{match.group(2)}"


def _extract_interference_factors(segments: list[str]) -> list[dict[str, str]]:
    factors: list[dict[str, str]] = []
    seen: set[str] = set()
    for segment in segments:
        for label, keywords in INTERFERENCE_PATTERNS:
            if label in seen:
                continue
            matched_keyword = next((keyword for keyword in keywords if keyword in segment), None)
            if matched_keyword:
                normalized_label = (
                    f"否认{label}" if _contains_negated(segment, matched_keyword) else label
                )
                factors.append({"label": normalized_label, "evidence": segment[:80]})
                seen.add(label)
    return factors


def _field_value(grouped: dict[str, list[str]], category: str) -> str | None:
    values = grouped.get(category, [])
    return "、".join(values) if values else None


def _chief_complaint(mentions: list[dict[str, str]], segments: list[str]) -> str:
    primary = [
        mention["label"]
        for mention in mentions
        if mention["category"]
        in {"mouth_thirst", "energy", "sleep", "urination", "stool", "appetite_digestive", "pain", "general"}
    ]
    if primary:
        return "、".join(primary[:5])
    return segments[0][:80] if segments else "未提供"


def _missing_fields(profile: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field_name, label in FIELD_LABELS.items():
        if not profile.get(field_name):
            missing.append(label)
    return missing


def _confidence(mentions: list[dict[str, str]], missing: list[str], raw_text: str) -> str:
    if not raw_text.strip():
        return "low"
    if len(mentions) >= 4 and len(missing) <= 2:
        return "high"
    if mentions:
        return "medium"
    return "low"


def _summary(profile: dict[str, Any], missing: list[str]) -> str:
    parts = [
        f"主诉/症状：{profile['chief_complaint']}",
        f"持续时间：{profile['duration']}" if profile.get("duration") else "",
        f"睡眠：{profile['sleep']}" if profile.get("sleep") else "",
        f"饮食：{profile['diet']}" if profile.get("diet") else "",
        f"饮水：{profile['water_intake']}" if profile.get("water_intake") else "",
        f"小便：{profile['urination']}" if profile.get("urination") else "",
        f"大便：{profile['stool']}" if profile.get("stool") else "",
    ]
    text = "；".join(part for part in parts if part)
    if missing:
        text = f"{text}。仍需补充：{'、'.join(missing[:4])}。"
    return text


def normalize_symptoms(
    symptom_text: str | None,
    *,
    symptom_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_text = (symptom_text or "").strip()
    structured_input = _clean_symptom_context(symptom_context)
    has_structured_input = bool(structured_input)
    if not raw_text and not has_structured_input:
        missing = ["主诉", *FIELD_LABELS.values()]
        return {
            "status": "skipped",
            "raw_text": "",
            "summary": "未提供症状文本，无法进行症状信息整理。",
            "symptom_profile": {
                "raw_text": "",
                "chief_complaint": "未提供",
                "duration": None,
                "sleep": None,
                "diet": None,
                "water_intake": None,
                "medication": None,
                "urination": None,
                "stool": None,
                "symptom_tags": [],
                "mentions": [],
                "interference_factors": [],
                "structured_input": {},
            },
            "missing_fields": missing,
            "follow_up_questions": ["请补充本次观察相关的主诉、持续时间、饮食饮水和近期用药情况。"],
            "confidence": "low",
            "safety_note": SAFETY_NOTE,
        }

    combined_text = "；".join(
        item for item in (raw_text, _context_text(structured_input)) if item
    )
    segments = _segments(combined_text)
    mentions, grouped = _extract_tags(segments)
    interference_factors = _extract_interference_factors(segments)

    if structured_input.get("medication"):
        medication = structured_input["medication"]
    elif any(item["label"] in {"否认近期用药", "否认保健品或维生素"} for item in interference_factors):
        medication = "否认近期用药/保健品"
    elif any(item["label"] in {"近期用药", "保健品或维生素"} for item in interference_factors):
        medication = "已提及"
    else:
        medication = None
    profile = {
        "raw_text": raw_text,
        "chief_complaint": structured_input.get("chief_complaint") or _chief_complaint(mentions, segments),
        "duration": structured_input.get("duration") or _extract_duration(combined_text),
        "sleep": structured_input.get("sleep") or _field_value(grouped, "sleep"),
        "diet": structured_input.get("diet") or _field_value(grouped, "diet"),
        "water_intake": structured_input.get("water_intake") or _field_value(grouped, "water_intake"),
        "medication": medication,
        "urination": structured_input.get("urination") or _field_value(grouped, "urination"),
        "stool": structured_input.get("stool") or _field_value(grouped, "stool"),
        "appetite_digestive": _field_value(grouped, "appetite_digestive"),
        "temperature": _field_value(grouped, "temperature"),
        "pain": _field_value(grouped, "pain"),
        "general": _field_value(grouped, "general"),
        "symptom_tags": [mention["label"] for mention in mentions],
        "mentions": mentions,
        "interference_factors": interference_factors,
        "structured_input": structured_input,
    }
    missing = _missing_fields(profile)

    return {
        "status": "completed",
        "raw_text": raw_text,
        "summary": _summary(profile, missing),
        "symptom_profile": profile,
        "missing_fields": missing,
        "follow_up_questions": [
            question
            for field_name, question in FOLLOW_UP_QUESTIONS.items()
            if FIELD_LABELS[field_name] in missing
        ],
        "confidence": _confidence(mentions, missing, raw_text),
        "safety_note": SAFETY_NOTE,
    }
