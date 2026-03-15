# Система распознавания рукописных документов

Веб-приложение для распознавания рукописного текста с изображений,
анализа и хранения данных.

## Локальный запуск на Windows (работает из любой папки: C:, D:, ZIP)

Если вы скачали архив с GitHub (например папка `ocr_project-main`) и распаковали в любое место,
скрипты ниже будут работать, пока вы запускаете их **из корня проекта**.

### 1) Что установить заранее
- **Python 3.10+** (с галочкой `Add Python to PATH`)
- **Node.js LTS** (npm ставится вместе с Node.js)
- **MongoDB** (опционально как Windows Service `MongoDB`)

### 2) Первый запуск (установка)
1. Откройте папку проекта.
2. Дважды кликните `install-local.bat`.

`install-local.bat`:
- проверит, что вы в правильной папке проекта,
- создаст `.venv` (если нет),
- установит backend зависимости,
- установит frontend зависимости,
- создаст маркер `.setup.done`.

### 3) Обычный запуск
- Двойной клик по `run-local.bat`.

Он поднимет:
- backend: `http://localhost:8000`
- frontend: `http://localhost:5173`

### 4) One-click вариант
- `start-local.bat` автоматически:
  - на первом запуске вызовет `install-local.bat`,
  - потом запустит `run-local.bat`.

### 5) Остановка
- Запустите `stop-local.bat`,
- или закройте окна **OCR Backend** и **OCR Frontend**.

## Jupyter playbook для теста рукописного OCR

Добавлен ноутбук: `notebooks/handwritten_text_playbook.ipynb`.

Он показывает:
- как загрузить модель TrOCR для рукописного текста,
- как прогнать OCR по вашему изображению,
- как протестировать на публичном IAM-сэмпле,
- какие библиотеки и датасеты лучше использовать для handwritten OCR.


## Если скрипты не сработали: запуск вручную через Command Prompt / PowerShell

Ниже полностью ручной способ: подтянуть изменения из GitHub и запустить backend/frontend командами.

### 1) Подтянуть последние изменения
Откройте терминал в папке проекта и выполните:

```bat
git fetch origin
git pull origin main
```

Если у вас проект был скачан как ZIP (без `.git`), проще заново скачать свежий ZIP с GitHub,
распаковать и открыть эту новую папку.

### 2) Backend (в отдельном окне терминала)
```bat
cd C:\path\to\ocr_project-main
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Если `py -3` не найден, замените на `python`:
```bat
python -m venv .venv
```

Backend будет доступен на `http://localhost:8000`.

### 3) Frontend (во втором отдельном окне терминала)
```bat
cd C:\path\to\ocr_project-main\frontend
npm install
npm run dev -- --host
```

Frontend будет доступен на `http://localhost:5173`.

### 4) Как останавливать
- В каждом окне нажмите `Ctrl + C`.
- Либо используйте `stop-local.bat`.