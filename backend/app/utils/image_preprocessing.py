import cv2


def autocrop_whitespace(image_path: str) -> str:
    image = cv2.imread(image_path)
    if image is None:
        return image_path

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    non_white_mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)[1]

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    non_white_mask = cv2.morphologyEx(non_white_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    non_white_mask = cv2.morphologyEx(non_white_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    points = cv2.findNonZero(non_white_mask)
    if points is None:
        return image_path

    x, y, w, h = cv2.boundingRect(points)
    padding = 20
    x0 = max(0, x - padding)
    y0 = max(0, y - padding)
    x1 = min(image.shape[1], x + w + padding)
    y1 = min(image.shape[0], y + h + padding)

    cropped = image[y0:y1, x0:x1]
    if cropped.size == 0:
        return image_path

    cv2.imwrite(image_path, cropped)
    return image_path
