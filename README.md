# Система распознавания рукописных документов

Веб-приложение для распознавания рукописного текста с изображений,
анализа и хранения данных.




demo 1 
https://www.icloud.com/iclouddrive/0265JxTq6IWXi6atOxfNpyV9g#Screen_Recording_2026-02-19_at_21.23.18
https://youtu.be/CXGAycsU29g


demo 2
https://www.icloud.com/iclouddrive/06fAsUzJ0A1RXN4fGju-vZjTw#Screen_Recording_2026-02-22_at_15.43.26
https://youtu.be/YaowND1KOx4

## Troubleshooting: `routes.py` shows undefined symbols in editor

If VS Code/Pylance reports errors like:
- `object_id_or_404 is not defined`
- `ImageEditRequest is not defined`
- `Image is not defined`
- `ImageOps is not defined`

then check **`backend/app/api/routes.py`** and make sure these parts exist in the same file:

1. Top imports:
   - `from PIL import Image, ImageOps`
   - `from bson import ObjectId`
   - `from pydantic import BaseModel, Field`
2. Helper function:
   - `def object_id_or_404(doc_id: str): ...`
3. Models before the image route:
   - `class CropRequest(BaseModel): ...`
   - `class ImageEditRequest(BaseModel): ...`
4. Route itself:
   - `@router.put("/documents/{doc_id}/image")`

If you copied only part of the diff previously, paste the full `routes.py` version from this repository branch.
