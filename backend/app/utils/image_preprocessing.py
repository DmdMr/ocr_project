import cv2


def _safe_crop_bounds(x: int, y: int, w: int, h: int, img_w: int, img_h: int, padding: int):
    x0 = max(0, x - padding)
    y0 = max(0, y - padding)
    x1 = min(img_w, x + w + padding)
    y1 = min(img_h, y + h + padding)
    return x0, y0, x1, y1


def _component_is_meaningful(
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    area: int,
    img_w: int,
    img_h: int,
    min_component_area: int,
    min_component_width: int,
    min_component_height: int,
    border_ignore_margin: int,
):
    if area < min_component_area or w < min_component_width or h < min_component_height:
        return False

    fill_ratio = area / float(max(1, w * h))
    aspect_ratio = w / float(max(1, h))

    touches_border = (
        x <= border_ignore_margin
        or y <= border_ignore_margin
        or x + w >= img_w - border_ignore_margin
        or y + h >= img_h - border_ignore_margin
    )

    is_thin_vertical = h > img_h * 0.35 and w <= 6
    is_thin_horizontal = w > img_w * 0.35 and h <= 6
    is_border_line = touches_border and (is_thin_vertical or is_thin_horizontal)
    is_sparse_tiny_blob = area < (min_component_area * 2) and fill_ratio < 0.08
    is_extreme_aspect = (aspect_ratio > 25 or aspect_ratio < 0.04) and touches_border

    if is_border_line or is_sparse_tiny_blob or is_extreme_aspect:
        return False

    return True


def _naive_content_bbox(mask):
    points = cv2.findNonZero(mask)
    if points is None:
        return None
    return cv2.boundingRect(points)


def autocrop_whitespace(
    image_path: str,
    *,
    padding: int = 20,
    white_threshold: int = 245,
    min_component_area: int = 80,
    min_component_width: int = 3,
    min_component_height: int = 3,
    border_ignore_margin: int = 8,
) -> str:
    image = cv2.imread(image_path)
    if image is None:
        return image_path

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    non_white_mask = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY_INV)[1]

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned_mask = cv2.morphologyEx(non_white_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    cleaned_mask = cv2.medianBlur(cleaned_mask, 3)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned_mask, connectivity=8)
    img_h, img_w = gray.shape[:2]
    meaningful_boxes = []

    for label in range(1, num_labels):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])

        if _component_is_meaningful(
            x=x,
            y=y,
            w=w,
            h=h,
            area=area,
            img_w=img_w,
            img_h=img_h,
            min_component_area=min_component_area,
            min_component_width=min_component_width,
            min_component_height=min_component_height,
            border_ignore_margin=border_ignore_margin,
        ):
            meaningful_boxes.append((x, y, w, h))

    if meaningful_boxes:
        min_x = min(box[0] for box in meaningful_boxes)
        min_y = min(box[1] for box in meaningful_boxes)
        max_x = max(box[0] + box[2] for box in meaningful_boxes)
        max_y = max(box[1] + box[3] for box in meaningful_boxes)
        crop_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)
    else:
        crop_bbox = _naive_content_bbox(cleaned_mask)

    if crop_bbox is None:
        return image_path

    x, y, w, h = crop_bbox
    x0, y0, x1, y1 = _safe_crop_bounds(x, y, w, h, img_w, img_h, padding)

    cropped = image[y0:y1, x0:x1]
    if cropped.size == 0:
        return image_path

    cv2.imwrite(image_path, cropped)
    return image_path
