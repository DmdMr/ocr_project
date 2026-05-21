import os
import json
import xml.etree.ElementTree as ET
from PIL import Image

# Пути к файлам (измените, если у вас другие названия)
XML_PATH = "annotations.xml"
RAW_IMAGES_DIR = "raw_cards"
OUTPUT_DIR = "dataset"
CROPS_DIR = os.path.join(OUTPUT_DIR, "line_crops")

# Создаем папки для результатов
os.makedirs(CROPS_DIR, exist_ok=True)

# Загружаем XML структуру CVAT
tree = ET.parse(XML_PATH)
root = tree.getroot()

annotations_list = []
crop_counter = 0

# Проходим по всем изображениям в файле разметки
for image_tag in root.findall('image'):
    image_name = image_tag.get('name')
    image_path = os.path.join(RAW_IMAGES_DIR, image_name)
    
    # Проверяем, существует ли исходная карточка
    if not os.path.exists(image_path):
        print(f"Предупреждение: Файл {image_name} не найден в папке {RAW_IMAGES_DIR}. Пропускаем.")
        continue
        
    # Открываем исходное изображение карточки
    with Image.open(image_path) as img:
        # Ищем все прямоугольники (строки текста) на этой карточке
        for box in image_tag.findall('box'):
            if box.get('label') == 'text_line':
                # Получаем координаты рамки (CVAT сохраняет их как float)
                xtl = float(box.get('xtl'))
                ytl = float(box.get('ytl'))
                xbr = float(box.get('xbr'))
                ybr = float(box.get('ybr'))
                
                # Получаем текст транскрипции из атрибута
                transcription = ""
                for attribute in box.findall('attribute'):
                    if attribute.get('name') == 'transcription':
                        transcription = attribute.text if attribute.text else ""
                
                # Генерируем уникальное имя для нарезанной полосы текста
                crop_counter += 1
                crop_filename = f"line_{crop_counter:04d}.png"
                crop_save_path = os.path.join(CROPS_DIR, crop_filename)
                
                # Обрезаем изображение по координатам (PIL требует целые числа int)
                cropped_img = img.crop((int(xtl), int(ytl), int(xbr), int(ybr)))
                
                # Сохраняем нарезанную строку
                cropped_img.save(crop_save_path)
                
                # Добавляем данные в структуру для JSON
                annotations_list.append({
                    "image_id": f"line_{crop_counter:04d}",
                    "file_path": f"line_crops/{crop_filename}",
                    "ground_truth": transcription.strip()
                })

# Формируем финальный JSON
output_json = {
    "dataset_metadata": {
        "language": "ru",
        "total_lines": len(annotations_list)
    },
    "annotations": annotations_list
}

# Записываем JSON на диск
json_save_path = os.path.join(OUTPUT_DIR, "labels.json")
with open(json_save_path, "w", encoding="utf-8") as f:
    json.dump(output_json, f, ensure_ascii=False, indent=2)

print(f"Успешно обработано! Нарезано строк: {len(annotations_list)}")
print(f"Файлы сохранены в папку: {OUTPUT_DIR}")
