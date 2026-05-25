# OCR Server Gateway

This folder contains a production-oriented OCR gateway layer (no local ML inference code).

## Architecture

Frontend → FastAPI gateway (`/ocr`) → provider router → (Ollama **or** GPU VPS OCR server) → unified OCR response.

## Unified response shape

```json
{
  "success": true,
  "text": "...",
  "provider": "ollama",
  "latency_ms": 123.45
}
```

## What this gateway does

- Routes incoming OCR requests to a selected provider (`OCR_PROVIDER=ollama|vps`).
- Uses configurable provider endpoints and request timeouts.
- Applies CORS for frontend integration.
- Returns consistent JSON errors.
- Logs runtime metrics to `logs/metrics.jsonl` for model evaluation, ops monitoring, and human-in-the-loop dataset improvement workflows.

## Run

```bash
cd server
pip install -r requirements.txt
cp .env.example .env
export $(grep -v '^#' .env | xargs)
uvicorn server:app --host 0.0.0.0 --port 8080
```
