# FB Auto-Poster v3 — Single Container + PostgreSQL

একটাই container। একটাই Dockerfile। Flask একসাথে API + frontend serve করে।

## Architecture

```
              ┌──────────────────────────────────┐
              │  Single Container (app)          │
              │  ┌──────────────────────────┐    │
              │  │  Flask (port 5000)       │    │
              │  │  ├─ /api/*      (API)    │    │
              │  │  ├─ /*          (static) │    │
              │  │  └─ background worker    │    │
              │  └──────────────────────────┘    │
              └────────────┬─────────────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │  PostgreSQL container    │
              └──────────────────────────┘
```

## কেন single container?

- Frontend + Backend আলাদা রাখার দরকার নেই এই প্রজেক্টে
- Next.js static export হয়ে pure HTML/CSS/JS হয়ে যায়
- Flask সেই ফাইলগুলো সরাসরি serve করে
- একটাই port, একটাই healthcheck, একটাই restart policy
- Coolify-তে সবচেয়ে simple deploy

## Deploy on Coolify

### Step 1: GitHub-এ push

এই repo-টা GitHub-এ push করুন।

### Step 2: Coolify-তে resource যোগ করুন

Coolify → **+ New Resource** → **Docker Compose** → repo select করুন।
`docker-compose.yml` (root) auto detect হবে।

### Step 3: Domain set করুন (শুধু `app` service এ)

Coolify-তে দুটো service দেখাবে: `app` আর `postgres`।

শুধু **`app`** service-এ যান → **Domains** → আপনার domain বসান
(যেমন `https://poster.yourdomain.com`)।

`postgres` service-এ domain set করবেন না।

### Step 4: Environment variables (optional)

ডিফল্ট value গুলো কাজ করবে। Production-এ change করুন:

- `SECRET_KEY` → যেকোনো random string
- `JWT_SECRET_KEY` → যেকোনো random string
- `POSTGRES_PASSWORD` → strong password (postgres DB-র জন্য)

### Step 5: Deploy

**Deploy** button এ চাপুন। ২-৩ মিনিট পরে build complete হবে।

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me-2026` | Flask session secret |
| `JWT_SECRET_KEY` | `jwt-change-me-2026` | JWT signing key |
| `POSTGRES_PASSWORD` | `fbpass_change_me_2026` | PostgreSQL password |
| `PORT` | `5000` | Container port (don't change) |
| `WORKER_TICK_SECONDS` | `30` | Worker check interval |
| `MAX_RETRIES` | `3` | Retry failed posts |
| `CSV_RETENTION_HOURS` | `24` | Hours to keep CSV |
| `CORS_ORIGINS` | `*` | Allowed origins |

## Local Dev

```bash
# Backend only (with SQLite fallback)
cd backend
pip install -r requirements.txt
python app.py
# → http://localhost:5000/api/health

# Frontend dev (with hot reload)
cd frontend
npm install
npm run dev
# → http://localhost:3000 (proxies /api to localhost:5000)
```

## CSV Format

```csv
caption,media_url,post_type
"Hello world!","https://example.com/image.jpg",image
"Check this out","https://example.com/video.mp4",video
```

## Troubleshooting

### Container restarts continuously

SSH তে যান:
```bash
docker logs fb-autoposter-app 2>&1 | tail -50
```

`FATAL:` line টা দেখুন — সেটাই আসল error।

### Database connection fails

PostgreSQL healthy কিনা দেখুন:
```bash
docker logs fb-autoposter-db 2>&1 | tail -20
```

### Frontend দেখাচ্ছে না (শুধু JSON দেখাচ্ছে)

মানে Dockerfile-এ Next.js build stage fail করেছে। Build logs দেখুন Coolify-তে।
