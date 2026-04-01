# Production Deployment Guide (Linux)

## 1) Server setup

1. Install system packages:
   - Python 3.11+ (or your target runtime)
   - Node.js 20+
   - Nginx
   - MongoDB 7 (or use managed MongoDB)
2. Create directories (example):
   - App code: `/opt/ocr_project`
   - Persistent uploads: `/srv/ocr_uploads`
   - Logs: `/var/log/ocr_project`
3. Clone repo to `/opt/ocr_project`.

---

## 2) Required environment variables

Set these for backend service:

- `ENVIRONMENT=production`
- `MONGO_URL=mongodb://127.0.0.1:27017`
- `MONGO_DB_NAME=ocr_database` (optional, defaults to `ocr_database`)
- `UPLOAD_DIR=/srv/ocr_uploads`
- `SECRET_KEY=<long-random-secret>`
- `FRONTEND_ORIGIN=https://your-frontend-domain.com`

Optional:

- `SESSION_TTL_DAYS=7`
- `SESSION_COOKIE_SECURE=true`
- `SESSION_COOKIE_SAMESITE=lax`

Notes:
- In production, backend startup will fail if `SECRET_KEY` or `FRONTEND_ORIGIN` is missing.
- `UPLOAD_DIR` supports external persistent storage outside the repository.

---

## 3) Backend run (production)

From project root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
npm run backend:prod
```

This runs Uvicorn with:
- `--proxy-headers`
- `--forwarded-allow-ips='*'`

So it behaves correctly behind Nginx reverse proxy headers.

---

## 4) Frontend build (production)

From project root:

```bash
cd frontend
npm ci
npm run build
```

Build output is generated in:
- `frontend/dist`

Serve `frontend/dist` using Nginx (recommended), not Vite dev server.

---

## 5) Nginx example configuration

```nginx
server {
    listen 80;
    server_name your-frontend-domain.com;

    root /opt/ocr_project/frontend/dist;
    index index.html;

    # Svelte SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Upload files proxy
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 6) Backups (MongoDB + uploads)

### MongoDB backup

```bash
mongodump --uri="mongodb://127.0.0.1:27017/ocr_database" --out /var/backups/ocr_project/mongo-$(date +%F)
```

### MongoDB restore

```bash
mongorestore --uri="mongodb://127.0.0.1:27017" /var/backups/ocr_project/mongo-YYYY-MM-DD/ocr_database
```

### Uploads backup

```bash
tar -czf /var/backups/ocr_project/uploads-$(date +%F).tar.gz /srv/ocr_uploads
```

### Uploads restore

```bash
tar -xzf /var/backups/ocr_project/uploads-YYYY-MM-DD.tar.gz -C /
```

---

## 7) Future plan (do not implement yet): MongoDB -> SQLite migration

### Proposed migration path

1. Introduce SQLAlchemy/SQLModel models side-by-side with current Mongo layer.
2. Add repository abstraction layer (services depend on interfaces, not direct Motor collections).
3. Implement SQLite repositories.
4. Add one-time data migration script from MongoDB documents to SQLite rows.
5. Run dual-read validation in staging, then cut over.

### Proposed tables/models

- `users`
  - `id`, `username`, `username_lower`, `password_hash`, `created_at`, `is_active`
- `sessions`
  - `id`, `session_id`, `user_id`, `created_at`, `expires_at`
- `documents`
  - `id`, `filename`, `display_filename`, `path`, `recognized_text`, `created_at`, `is_archived`, `archived_at`, etc.
- `document_gallery_images`
  - `id`, `document_id`, `filename`, `path`, `file_hash`, `recognized_text`, `created_at`, `image_version`
- `document_attachments`
  - `id`, `document_id`, `filename`, `path`, `original_name`, `content_type`, `size`, `created_at`
- `document_tags` (many-to-many)
  - `document_id`, `tag_id`
- `tags`
  - `id`, `name`, `created_at`
- `app_settings`
  - `id`, `json_blob` (or normalized settings tables)
- `custom_fields`
  - `id`, `name`, `type`, `created_at`
- `document_custom_field_values`
  - `document_id`, `custom_field_id`, `text_value`, `number_value`

### Routes needing refactor

- Auth routes:
  - `/api/auth/register`
  - `/api/auth/login`
  - `/api/auth/logout`
  - `/api/auth/me`
- Document CRUD/search/archive routes:
  - `/api/documents*`, archive/restore/delete endpoints
- Upload and gallery/attachment routes:
  - `/api/upload`
  - `/api/documents/{id}/gallery*`
  - `/api/documents/{id}/attachments*`
- Tags/settings/custom field routes:
  - tag CRUD endpoints
  - settings and custom field endpoints

