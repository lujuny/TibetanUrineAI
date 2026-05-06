from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from app.core.config import get_settings
from app.services.gemma_features import FEATURE_KEYS, review_visual_features_with_gemma


FOAM_SEVERITY = {
    "未见明显泡沫": 0,
    "少量泡沫": 1,
    "较多泡沫": 2,
}


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


def _feature(
    label: str,
    confidence: float,
    evidence: str,
    *,
    metrics: dict[str, Any] | None = None,
    source: str = "rule_cv",
) -> dict[str, Any]:
    return {
        "label": label,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "evidence": evidence,
        "source": source,
        "metrics": metrics or {},
    }


def _image_pixels(image: Image.Image) -> list[tuple[int, int, int]]:
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def _urine_mask_pixels(
    image: Image.Image,
) -> tuple[list[tuple[int, int, int]], float, int, Image.Image, tuple[int, int, int, int] | None]:
    sample = image.convert("RGB")
    sample.thumbnail((700, 700))
    hsv = sample.convert("HSV")
    rgb_pixels = _image_pixels(sample)
    hsv_pixels = _image_pixels(hsv)
    selected: list[tuple[int, int, int]] = []
    mask = Image.new("L", sample.size, 0)

    for index, (rgb, (hue, saturation, value)) in enumerate(zip(rgb_pixels, hsv_pixels)):
        if 8 <= hue <= 50 and saturation >= 30 and 45 <= value <= 245:
            selected.append(rgb)
            mask.putpixel((index % sample.width, index // sample.width), 255)

    total = max(len(rgb_pixels), 1)
    if len(selected) < max(32, int(len(rgb_pixels) * 0.004)):
        full_mask = Image.new("L", sample.size, 255)
        return rgb_pixels, 0.0, total, full_mask, full_mask.getbbox()
    return selected, len(selected) / total, total, mask, mask.getbbox()


def _average_rgb(pixels: list[tuple[int, int, int]]) -> tuple[float, float, float]:
    if not pixels:
        return 0.0, 0.0, 0.0
    red = mean(pixel[0] for pixel in pixels)
    green = mean(pixel[1] for pixel in pixels)
    blue = mean(pixel[2] for pixel in pixels)
    return red, green, blue


def _rgb_to_hsv_metrics(red: float, green: float, blue: float) -> dict[str, float]:
    pil_pixel = Image.new("RGB", (1, 1), (round(red), round(green), round(blue)))
    hue, saturation, value = pil_pixel.convert("HSV").getpixel((0, 0))
    return {
        "hue_degrees": round(hue * 360 / 255, 2),
        "saturation": round(saturation / 255, 4),
        "value": round(value / 255, 4),
    }


def _color_feature(pixels: list[tuple[int, int, int]]) -> dict[str, Any]:
    red, green, blue = _average_rgb(pixels)
    hsv = _rgb_to_hsv_metrics(red, green, blue)
    hue = hsv["hue_degrees"]
    saturation = hsv["saturation"]
    value = hsv["value"]

    if value < 0.34:
        label = "棕黄色"
    elif saturation < 0.18 and value > 0.72:
        label = "淡黄色"
    elif hue < 24:
        label = "橙黄色"
    elif value < 0.52:
        label = "深黄色"
    elif value > 0.76:
        label = "淡黄色"
    else:
        label = "黄色"

    confidence = 0.62 + min(saturation, 0.38)
    return _feature(
        label,
        confidence,
        f"尿液色彩区域平均 RGB 约为 {round(red)}/{round(green)}/{round(blue)}。",
        metrics={
            "avg_red": round(red, 2),
            "avg_green": round(green, 2),
            "avg_blue": round(blue, 2),
            **hsv,
        },
    )


def _transparency_feature(gray: Image.Image, urine_ratio: float) -> dict[str, Any]:
    contrast = float(ImageStat.Stat(gray).stddev[0])
    edge_strength = float(ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0])
    clarity_score = contrast * 0.7 + edge_strength * 4.0

    if clarity_score >= 34 and urine_ratio >= 0.03:
        label = "清亮"
        confidence = 0.72
    elif clarity_score >= 22:
        label = "轻度浑浊"
        confidence = 0.66
    else:
        label = "明显浑浊"
        confidence = 0.62

    return _feature(
        label,
        confidence,
        "基于灰度对比度、边缘强度和尿液色彩区域占比估算透明度。",
        metrics={
            "contrast": round(contrast, 2),
            "edge_strength": round(edge_strength, 2),
            "clarity_score": round(clarity_score, 2),
        },
    )


def _connected_components(mask: Image.Image) -> list[dict[str, int]]:
    width, height = mask.size
    data = mask.load()
    seen: set[tuple[int, int]] = set()
    components: list[dict[str, int]] = []

    for y in range(height):
        for x in range(width):
            if not data[x, y] or (x, y) in seen:
                continue

            stack = [(x, y)]
            seen.add((x, y))
            area = 0
            min_x = max_x = x
            min_y = max_y = y

            while stack:
                current_x, current_y = stack.pop()
                area += 1
                min_x = min(min_x, current_x)
                max_x = max(max_x, current_x)
                min_y = min(min_y, current_y)
                max_y = max(max_y, current_y)

                for next_y in range(current_y - 1, current_y + 2):
                    for next_x in range(current_x - 1, current_x + 2):
                        if next_x < 0 or next_y < 0 or next_x >= width or next_y >= height:
                            continue
                        if (next_x, next_y) in seen or not data[next_x, next_y]:
                            continue
                        seen.add((next_x, next_y))
                        stack.append((next_x, next_y))

            components.append(
                {
                    "area": area,
                    "width": max_x - min_x + 1,
                    "height": max_y - min_y + 1,
                    "min_x": min_x,
                    "min_y": min_y,
                    "max_x": max_x,
                    "max_y": max_y,
                }
            )

    return components


def _foam_feature(
    image: Image.Image,
    urine_mask: Image.Image,
    urine_ratio: float,
) -> dict[str, Any]:
    sample = image.convert("RGB")
    sample.thumbnail((700, 700))
    hsv = sample.convert("HSV")
    edges = sample.convert("L").filter(ImageFilter.FIND_EDGES)
    if urine_mask.size != sample.size:
        urine_mask = urine_mask.resize(sample.size)

    urine_bbox = urine_mask.getbbox()
    if not urine_bbox:
        return _feature(
            "未见明显泡沫",
            0.55,
            "未定位到稳定尿液主体区域，泡沫判断保持保守。",
            metrics={
                "foam_candidate_ratio": 0,
                "valid_foam_component_count": 0,
                "ignored_bright_region_ratio": 0,
            },
        )

    near_urine_mask = urine_mask.filter(ImageFilter.MaxFilter(17))
    candidate_mask = Image.new("L", sample.size, 0)
    hsv_pixels = _image_pixels(hsv)
    edge_pixels = _image_pixels(edges)
    urine_pixels = _image_pixels(urine_mask)
    near_urine_pixels = _image_pixels(near_urine_mask)
    width, height = sample.size
    x0, y0, x1, y1 = urine_bbox
    inset_x = max(2, int((x1 - x0) * 0.035))
    inset_y = max(2, int((y1 - y0) * 0.035))
    search_box = (x0 + inset_x, y0 + inset_y, x1 - inset_x, y1 - inset_y)

    raw_bright_count = 0
    candidate_count = 0
    texture_edge_count = 0
    upper_texture_edge_count = 0
    right_texture_edge_count = 0
    bright_texture_edge_count = 0
    search_area = max((search_box[2] - search_box[0]) * (search_box[3] - search_box[1]), 1)
    for index, (hue, saturation, value) in enumerate(hsv_pixels):
        x = index % width
        y = index // width
        in_search_box = search_box[0] <= x < search_box[2] and search_box[1] <= y < search_box[3]

        if (
            in_search_box
            and near_urine_pixels[index]
            and edge_pixels[index] > 35
            and 70 < value < 245
        ):
            texture_edge_count += 1
            if y < y0 + (y1 - y0) * 0.58:
                upper_texture_edge_count += 1
            if x > x0 + (x1 - x0) * 0.45:
                right_texture_edge_count += 1
            if value > 180 and saturation < 140:
                bright_texture_edge_count += 1

        if value < 222 or saturation > 68:
            continue

        raw_bright_count += 1
        if not in_search_box:
            continue
        if not near_urine_pixels[index]:
            continue

        candidate_mask.putpixel((x, y), 255)
        candidate_count += 1

    urine_area = max(sum(1 for value in urine_pixels if value), 1)
    max_component_area = max(10, int(urine_area * 0.025))
    min_component_area = 3
    valid_components: list[dict[str, int]] = []
    ignored_components: list[dict[str, int]] = []

    for component in _connected_components(candidate_mask):
        area = component["area"]
        component_width = component["width"]
        component_height = component["height"]
        aspect_ratio = component_width / max(component_height, 1)
        too_large = area > max_component_area
        too_linear = aspect_ratio > 8 or aspect_ratio < 0.125
        if area < min_component_area or too_large or too_linear:
            ignored_components.append(component)
            continue
        valid_components.append(component)

    valid_area = sum(component["area"] for component in valid_components)
    ignored_area = sum(component["area"] for component in ignored_components)
    foam_ratio = valid_area / urine_area
    raw_ratio = raw_bright_count / max(len(hsv_pixels), 1)
    candidate_ratio = candidate_count / urine_area
    texture_edge_ratio = texture_edge_count / search_area
    upper_texture_edge_ratio = upper_texture_edge_count / search_area
    right_texture_edge_ratio = right_texture_edge_count / search_area
    bright_texture_edge_ratio = bright_texture_edge_count / search_area

    heavy_texture_signal = (
        texture_edge_ratio >= 0.065
        and (
            upper_texture_edge_ratio >= 0.035
            or right_texture_edge_ratio >= 0.055
            or bright_texture_edge_ratio >= 0.02
        )
    )
    light_texture_signal = texture_edge_ratio >= 0.032 and (
        upper_texture_edge_ratio >= 0.014
        or right_texture_edge_ratio >= 0.02
        or bright_texture_edge_ratio >= 0.008
    )
    bright_component_signal = foam_ratio >= 0.018 and len(valid_components) >= 10
    subtle_component_signal = foam_ratio >= 0.02 and len(valid_components) >= 8

    if heavy_texture_signal and urine_ratio >= 0.015:
        label = "较多泡沫"
        confidence = 0.72
    elif light_texture_signal or bright_component_signal or subtle_component_signal:
        label = "少量泡沫"
        confidence = 0.62
    else:
        label = "未见明显泡沫"
        confidence = 0.64

    evidence = (
        "尿液主体或液面边缘附近可见少量小面积高亮低饱和点状区域，"
        "按少量泡沫处理，并排除背景、杯壁边缘和大面积反光。"
        if label == "少量泡沫"
        else "仅统计尿液主体附近的小面积高亮低饱和成簇区域，并排除背景、杯壁边缘和大面积反光。"
    )

    return _feature(
        label,
        confidence,
        evidence,
        metrics={
            "raw_bright_low_saturation_ratio": round(raw_ratio, 4),
            "near_urine_candidate_ratio": round(candidate_ratio, 4),
            "foam_candidate_ratio": round(foam_ratio, 4),
            "foam_texture_edge_ratio": round(texture_edge_ratio, 4),
            "upper_texture_edge_ratio": round(upper_texture_edge_ratio, 4),
            "right_texture_edge_ratio": round(right_texture_edge_ratio, 4),
            "bright_texture_edge_ratio": round(bright_texture_edge_ratio, 4),
            "valid_foam_component_count": len(valid_components),
            "ignored_bright_component_count": len(ignored_components),
            "ignored_bright_region_ratio": round(ignored_area / urine_area, 4),
        },
    )


def _foam_severity(label: str | None) -> int:
    return FOAM_SEVERITY.get(str(label or "").strip(), -1)


def _is_specific_foam_evidence(evidence: str) -> bool:
    normalized = evidence.strip()
    if not normalized:
        return False

    generic_markers = (
        "高亮低饱和",
        "占比",
        "规则",
        "CV",
        "粗略估算",
        "初步结果",
        "基于",
    )
    if any(marker in normalized for marker in generic_markers):
        return False

    specific_markers = (
        "气泡",
        "泡沫点",
        "白色泡沫",
        "成簇",
        "尿液表面",
        "表面可见",
        "浮沫",
    )
    return any(marker in normalized for marker in specific_markers)


def _fuse_foam_feature(rule_item: dict[str, Any], gemma_item: dict[str, Any]) -> dict[str, Any]:
    rule_label = rule_item.get("label")
    gemma_label = gemma_item.get("label")
    rule_severity = _foam_severity(rule_label)
    gemma_severity = _foam_severity(gemma_label)
    gemma_confidence = float(gemma_item.get("confidence") or 0)
    gemma_evidence = str(gemma_item.get("evidence") or "")
    confidence_threshold = 0.78 if gemma_label == "较多泡沫" else 0.68

    if (
        gemma_severity > rule_severity
        and (
            gemma_confidence < confidence_threshold
            or not _is_specific_foam_evidence(gemma_evidence)
        )
    ):
        return {
            **rule_item,
            "rule_label": rule_label,
            "gemma_label": gemma_label,
            "source": "rule_cv_conservative",
            "evidence": (
                f"{rule_item.get('evidence', '')}"
                " Gemma4 尝试上调泡沫等级，但缺少明确的气泡/泡沫点证据，"
                "因此按保守规则保留原判断。"
            ).strip(),
            "gemma_evidence": gemma_evidence,
        }

    return {
        **gemma_item,
        "rule_label": rule_label,
        "gemma_label": gemma_label,
        "source": "rule_cv+gemma4",
        "evidence": gemma_item.get("evidence") or rule_item.get("evidence", ""),
        "metrics": rule_item.get("metrics", {}),
    }


def _sediment_feature(pixels: list[tuple[int, int, int]]) -> dict[str, Any]:
    if not pixels:
        ratio = 0.0
    else:
        hsv_image = Image.new("RGB", (len(pixels), 1))
        hsv_image.putdata(pixels)
        hsv_pixels = _image_pixels(hsv_image.convert("HSV"))
        dark_sat = sum(
            1
            for hue, saturation, value in hsv_pixels
            if value <= 95 and saturation >= 45
        )
        ratio = dark_sat / len(hsv_pixels)

    if ratio >= 0.18:
        label = "明显沉淀"
        confidence = 0.67
    elif ratio >= 0.06:
        label = "少量沉淀"
        confidence = 0.62
    else:
        label = "未见明显沉淀"
        confidence = 0.6

    return _feature(
        label,
        confidence,
        "基于尿液色彩区域中的低亮度高饱和像素占比估算沉淀风险。",
        metrics={"dark_saturated_ratio": round(ratio, 4)},
    )


def _layering_feature(image: Image.Image) -> dict[str, Any]:
    sample = image.convert("L")
    sample.thumbnail((700, 700))
    width, height = sample.size
    if height < 3:
        band_means = [0.0, 0.0, 0.0]
    else:
        bands = [
            sample.crop((0, 0, width, height // 3)),
            sample.crop((0, height // 3, width, 2 * height // 3)),
            sample.crop((0, 2 * height // 3, width, height)),
        ]
        band_means = [float(ImageStat.Stat(band).mean[0]) for band in bands]

    spread = max(band_means) - min(band_means)
    if spread >= 42:
        label = "明显分层"
        confidence = 0.64
    elif spread >= 24:
        label = "疑似分层"
        confidence = 0.58
    else:
        label = "未见明显分层"
        confidence = 0.62

    return _feature(
        label,
        confidence,
        "基于图像上中下三个水平带的亮度差异估算分层。",
        metrics={
            "top_brightness": round(band_means[0], 2),
            "middle_brightness": round(band_means[1], 2),
            "bottom_brightness": round(band_means[2], 2),
            "band_brightness_spread": round(spread, 2),
        },
    )


def _fuse_features(
    *,
    rule_result: dict[str, Any],
    gemma_review: dict[str, Any],
) -> dict[str, Any]:
    if gemma_review.get("status") != "completed":
        return {
            "status": "completed",
            "features": rule_result["features"],
            "summary": rule_result["summary"],
            "recommendations": rule_result["recommendations"],
            "rule_cv_result": rule_result,
            "gemma_review": gemma_review,
        }

    fused = dict(rule_result["features"])
    gemma_features = gemma_review.get("features", {})
    for key in FEATURE_KEYS:
        gemma_item = gemma_features.get(key)
        if not gemma_item:
            continue

        rule_item = fused.get(key, {})
        if key == "foam":
            fused[key] = _fuse_foam_feature(rule_item, gemma_item)
            continue

        fused[key] = {
            **gemma_item,
            "rule_label": rule_item.get("label"),
            "gemma_label": gemma_item.get("label"),
            "source": "rule_cv+gemma4",
            "evidence": gemma_item.get("evidence") or rule_item.get("evidence", ""),
            "metrics": rule_item.get("metrics", {}),
        }

    recommendations = [
        *rule_result["recommendations"],
        *gemma_review.get("recommendations", []),
    ]
    unique_recommendations = list(dict.fromkeys(item for item in recommendations if item))

    return {
        "status": "completed",
        "features": fused,
        "summary": gemma_review.get("summary") or rule_result["summary"],
        "recommendations": unique_recommendations,
        "rule_cv_result": rule_result,
        "gemma_review": gemma_review,
    }


def extract_visual_features(image_path: str | None, include_gemma: bool = True) -> dict[str, Any]:
    if not image_path:
        return {
            "status": "failed",
            "features": {},
            "summary": "未提供图像，无法提取视觉特征。",
            "recommendations": ["请先上传尿液样本图像。"],
            "gemma_review": {
                "status": "skipped",
                "provider": "gemma4",
                "reason": "No image was provided.",
            },
        }

    image_file = _resolve_image_file(image_path)
    if not image_file.exists():
        return {
            "status": "failed",
            "features": {},
            "summary": "图像文件不存在，无法提取视觉特征。",
            "recommendations": ["请重新上传尿液样本图像。"],
            "gemma_review": {
                "status": "skipped",
                "provider": "gemma4",
                "reason": "Image file was not found.",
            },
        }

    try:
        with Image.open(image_file) as image:
            image.load()
            rgb = image.convert("RGB")
            gray = image.convert("L")
    except (OSError, UnidentifiedImageError):
        return {
            "status": "failed",
            "features": {},
            "summary": "图像文件无法正常解析，无法提取视觉特征。",
            "recommendations": ["请上传可正常打开的 JPG、PNG 或 WEBP 图像。"],
            "gemma_review": {
                "status": "skipped",
                "provider": "gemma4",
                "reason": "Image could not be parsed.",
            },
        }

    (
        urine_pixels,
        urine_ratio,
        sample_pixel_count,
        urine_mask,
        _urine_bbox,
    ) = _urine_mask_pixels(rgb)

    features = {
        "color": _color_feature(urine_pixels),
        "transparency": _transparency_feature(gray, urine_ratio),
        "foam": _foam_feature(rgb, urine_mask, urine_ratio),
        "sediment": _sediment_feature(urine_pixels),
        "layering": _layering_feature(rgb),
    }
    metrics = {
        "width": rgb.width,
        "height": rgb.height,
        "urine_like_pixel_count": len(urine_pixels),
        "urine_like_pixel_ratio": round(urine_ratio, 4),
        "sample_pixel_count": sample_pixel_count,
    }
    summary = "；".join(
        [
            f"颜色{features['color']['label']}",
            f"透明度{features['transparency']['label']}",
            f"泡沫{features['foam']['label']}",
            f"沉淀{features['sediment']['label']}",
            f"分层{features['layering']['label']}",
        ]
    )
    rule_result = {
        "status": "completed",
        "features": features,
        "summary": summary,
        "recommendations": ["视觉特征为辅助观察结果，需结合采集条件和专业复核。"],
        "metrics": metrics,
    }

    if not include_gemma:
        return _fuse_features(
            rule_result=rule_result,
            gemma_review={
                "status": "skipped",
                "provider": "gemma4",
                "reason": "Gemma4 review was not requested.",
            },
        )

    gemma_review = review_visual_features_with_gemma(
        image_file=image_file,
        rule_result=rule_result,
    )
    return _fuse_features(rule_result=rule_result, gemma_review=gemma_review)
