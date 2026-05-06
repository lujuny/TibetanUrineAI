from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from app.core.config import get_settings
from app.services.gemma_quality import review_image_quality_with_gemma


def _issue(issue_type: str, severity: str, message: str) -> dict[str, str]:
    return {"type": issue_type, "severity": severity, "message": message}


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _resolve_image_file(image_path: str) -> Path:
    if image_path.startswith("/uploads/"):
        upload_root = Path(get_settings().upload_dir).resolve()
        relative_path = image_path.removeprefix("/uploads/").lstrip("/")
        candidate = (upload_root / relative_path).resolve()
        try:
            candidate.relative_to(upload_root)
        except ValueError:
            return upload_root / "__invalid_upload_path__"
        return candidate
    return Path(image_path)


def _recommendations_for_issues(issues: list[dict[str, str]]) -> list[str]:
    if not issues:
        return ["图像质量可用，可进入后续视觉特征分析。"]

    recommendations: list[str] = []
    issue_types = {item["type"] for item in issues}

    if "missing_image" in issue_types or "file_not_found" in issue_types:
        recommendations.append("请重新上传尿液样本图像。")
    if "invalid_image" in issue_types:
        recommendations.append("请上传可正常打开的 JPG、PNG 或 WEBP 图像。")
    if "low_resolution" in issue_types:
        recommendations.append("请使用更高分辨率图像，尽量保证样本区域清晰完整。")
    if "underexposed" in issue_types:
        recommendations.append("请增加环境光或靠近稳定光源重新拍摄。")
    if "overexposed" in issue_types or "highlight_reflection" in issue_types:
        recommendations.append("请避开强反光和直射光，调整角度后重新拍摄。")
    if "low_contrast" in issue_types:
        recommendations.append("请使用白色或浅色背景，并让尿液样本与背景边界更清楚。")
    if "blurred" in issue_types:
        recommendations.append("请保持设备稳定，重新拍摄清晰图像。")

    return recommendations or ["建议重新采集一张更清晰、光照更稳定的图像。"]


def _urine_like_pixel_ratio(image: Image.Image) -> float:
    sample = image.convert("RGB")
    sample.thumbnail((512, 512))
    hsv = sample.convert("HSV")
    if hasattr(hsv, "get_flattened_data"):
        pixels = list(hsv.get_flattened_data())
    else:
        pixels = list(hsv.getdata())
    if not pixels:
        return 0.0

    urine_like = 0
    for hue, saturation, value in pixels:
        if 8 <= hue <= 48 and saturation >= 35 and 45 <= value <= 245:
            urine_like += 1
    return urine_like / len(pixels)


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for issue in issues:
        key = (str(issue.get("type")), str(issue.get("message")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique


def _dedupe_recommendations(recommendations: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in recommendations:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _gemma_penalty(review: dict[str, Any]) -> int:
    if review.get("status") != "completed":
        return 0

    penalty = 0
    severity_penalty = {"high": 18, "medium": 9, "low": 4}
    for issue in review.get("issues", []):
        penalty += severity_penalty.get(str(issue.get("severity")), 9)

    if review.get("collection_quality") == "poor":
        penalty += 18
    elif review.get("collection_quality") == "acceptable":
        penalty += 4

    if review.get("sample_visible") is False:
        penalty += 20
    if review.get("urine_region_complete") is False:
        penalty += 12
    if review.get("reflection_risk") in {"moderate", "severe"}:
        penalty += 8 if review.get("reflection_risk") == "moderate" else 16
    if review.get("blur_risk") in {"moderate", "severe"}:
        penalty += 8 if review.get("blur_risk") == "moderate" else 16

    return min(penalty, 45)


def _fuse_rule_and_gemma(
    *,
    rule_result: dict[str, Any],
    gemma_review: dict[str, Any],
) -> dict[str, Any]:
    if gemma_review.get("status") != "completed":
        return {
            **rule_result,
            "gemma_review": gemma_review,
            "score_sources": {
                "rule_cv_score": rule_result["quality_score"],
                "gemma_penalty": 0,
                "fusion_method": "rule_cv_only",
            },
        }

    gemma_issues = gemma_review.get("issues", [])
    issues = _dedupe_issues([*rule_result["issues"], *gemma_issues])
    recommendations = _dedupe_recommendations(
        [
            *rule_result["recommendations"],
            *gemma_review.get("recommendations", []),
        ]
    )
    penalty = _gemma_penalty(gemma_review)
    quality_score = _clamp_score(rule_result["quality_score"] - penalty)
    high_severity_count = sum(1 for item in issues if item.get("severity") == "high")
    usable = quality_score >= 60 and high_severity_count == 0

    return {
        **rule_result,
        "quality_score": quality_score,
        "usable": usable,
        "issues": issues,
        "recommendations": recommendations,
        "gemma_review": gemma_review,
        "score_sources": {
            "rule_cv_score": rule_result["quality_score"],
            "gemma_penalty": penalty,
            "fusion_method": "rule_cv_score_minus_gemma_penalty",
        },
    }


def assess_image_quality(image_path: str | None, include_gemma: bool = True) -> dict[str, Any]:
    if not image_path:
        issues = [_issue("missing_image", "high", "未提供图像。")]
        return {
            "quality_score": 0,
            "usable": False,
            "issues": issues,
            "recommendations": _recommendations_for_issues(issues),
            "metrics": {},
            "gemma_review": {
                "status": "skipped",
                "provider": "gemma4",
                "reason": "No image was provided.",
            },
            "score_sources": {
                "rule_cv_score": 0,
                "gemma_penalty": 0,
                "fusion_method": "rule_cv_only",
            },
        }

    image_file = _resolve_image_file(image_path)
    if not image_file.exists():
        issues = [_issue("file_not_found", "high", "图像文件不存在，无法检测质量。")]
        return {
            "quality_score": 0,
            "usable": False,
            "issues": issues,
            "recommendations": _recommendations_for_issues(issues),
            "metrics": {"image_path": image_path},
            "gemma_review": {
                "status": "skipped",
                "provider": "gemma4",
                "reason": "Image file was not found.",
            },
            "score_sources": {
                "rule_cv_score": 0,
                "gemma_penalty": 0,
                "fusion_method": "rule_cv_only",
            },
        }

    try:
        with Image.open(image_file) as image:
            image.load()
            width, height = image.size
            rgb = image.convert("RGB")
            gray = image.convert("L")
    except (OSError, UnidentifiedImageError):
        issues = [_issue("invalid_image", "high", "图像文件无法正常解析。")]
        return {
            "quality_score": 0,
            "usable": False,
            "issues": issues,
            "recommendations": _recommendations_for_issues(issues),
            "metrics": {"image_path": image_path},
            "gemma_review": {
                "status": "skipped",
                "provider": "gemma4",
                "reason": "Image could not be parsed.",
            },
            "score_sources": {
                "rule_cv_score": 0,
                "gemma_penalty": 0,
                "fusion_method": "rule_cv_only",
            },
        }

    stat = ImageStat.Stat(gray)
    brightness = float(stat.mean[0])
    contrast = float(stat.stddev[0])
    histogram = gray.histogram()
    total_pixels = max(width * height, 1)
    dark_pixel_ratio = sum(histogram[:35]) / total_pixels
    bright_pixel_ratio = sum(histogram[235:]) / total_pixels

    edge_image = gray.filter(ImageFilter.FIND_EDGES)
    edge_strength = float(ImageStat.Stat(edge_image).mean[0])
    urine_like_ratio = _urine_like_pixel_ratio(rgb)
    min_side = min(width, height)

    issues: list[dict[str, str]] = []
    score = 100

    if min_side < 320:
        issues.append(_issue("low_resolution", "high", "图像分辨率过低，关键细节可能无法判断。"))
        score -= 40
    elif min_side < 640:
        issues.append(_issue("low_resolution", "medium", "图像分辨率偏低，建议使用更清晰的照片。"))
        score -= 20

    if brightness < 45 or dark_pixel_ratio > 0.45:
        issues.append(_issue("underexposed", "high", "图像明显偏暗，尿液颜色和沉淀不易辨认。"))
        score -= 30
    elif brightness < 70:
        issues.append(_issue("underexposed", "medium", "图像亮度偏低。"))
        score -= 15

    if brightness > 225 or bright_pixel_ratio > 0.45:
        issues.append(_issue("overexposed", "high", "图像明显过曝，可能丢失颜色和泡沫细节。"))
        score -= 30
    elif brightness > 205:
        issues.append(_issue("overexposed", "medium", "图像亮度偏高。"))
        score -= 15

    if bright_pixel_ratio > 0.18 and brightness > 175:
        issues.append(_issue("highlight_reflection", "medium", "图像中高亮区域较多，可能存在反光干扰。"))
        score -= 10

    if contrast < 18:
        issues.append(_issue("low_contrast", "medium", "图像对比度偏低，样本边界不够清楚。"))
        score -= 18

    if edge_strength < 3.0:
        issues.append(_issue("blurred", "high", "图像边缘信息很弱，疑似模糊或严重失焦。"))
        score -= 30
    elif edge_strength < 5.5:
        issues.append(_issue("blurred", "medium", "图像清晰度偏低，建议重新拍摄。"))
        score -= 15

    if urine_like_ratio < 0.005:
        issues.append(_issue("sample_region_not_obvious", "medium", "CV 初筛未发现明显尿液色彩区域，样本可能过小或背景干扰较强。"))
        score -= 10
    elif urine_like_ratio < 0.02:
        issues.append(_issue("sample_region_small", "low", "CV 初筛显示尿液色彩区域占比较小。"))
        score -= 5

    high_severity_count = sum(1 for item in issues if item["severity"] == "high")
    quality_score = _clamp_score(score)
    usable = quality_score >= 60 and high_severity_count == 0

    rule_result = {
        "quality_score": quality_score,
        "usable": usable,
        "issues": issues,
        "recommendations": _recommendations_for_issues(issues),
        "metrics": {
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "edge_strength": round(edge_strength, 2),
            "dark_pixel_ratio": round(dark_pixel_ratio, 4),
            "bright_pixel_ratio": round(bright_pixel_ratio, 4),
            "urine_like_pixel_ratio": round(urine_like_ratio, 4),
        },
        "rule_cv_result": {
            "quality_score": quality_score,
            "usable": usable,
            "issues": issues,
        },
    }

    if not include_gemma:
        return _fuse_rule_and_gemma(
            rule_result=rule_result,
            gemma_review={
                "status": "skipped",
                "provider": "gemma4",
                "reason": "Gemma4 review was not requested.",
            },
        )

    gemma_review = review_image_quality_with_gemma(
        image_file=image_file,
        rule_result=rule_result,
    )
    return _fuse_rule_and_gemma(rule_result=rule_result, gemma_review=gemma_review)
