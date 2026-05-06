HIGH_RISK_TERMS = [
    "确诊",
    "诊断为",
    "治疗方案",
    "必须服用",
    "处方",
]

SAFETY_NOTE = (
    "本结果仅用于辅助观察和记录，不作为确诊或治疗依据，"
    "需由专业藏医师结合完整问诊复核。"
)


def contains_high_risk_terms(text: str) -> bool:
    return any(term in text for term in HIGH_RISK_TERMS)


def append_safety_note(text: str) -> str:
    if SAFETY_NOTE in text:
        return text
    return f"{text}\n\n{SAFETY_NOTE}"

