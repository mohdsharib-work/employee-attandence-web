# Face Recognition Attendance System — Web

Full-stack attendance dashboard: **React + Vite** (frontend) · **FastAPI** (backend) · **Turso / SQLite** (database).

---

## Project Structure

```
project/
├── backend/
│   ├── api/
│   │   ├── dependencies.py        # JWT, DB session, API-key guards
│   │   └── routes/                # auth · employee · attendance · reports
│   ├── config/settings.py         # All config via environment variables
│   ├── database/connection.py     # SQLAlchemy — auto-detects Turso vs local SQLite
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── services/                  # Business logic
│   ├── main.py                    # FastAPI entry point
│   ├── seed_admin.py              # ← run once to create first admin user
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/            # Layout, AttendanceTable, EmployeeCard, charts
│   │   ├── pages/                 # Dashboard · Employees · Reports · Settings · Login
│   │   ├── services/api.js        # Axios client (reads VITE_API_URL)
│   │   ├── store/                 # Zustand: authStore · attendanceStore
│   │   └── utils/                 # formatDate · exportCSV
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── render.yaml                    # Render Blueprint (backend deploy)
└── .gitignore
```

---

## Local Development

### Prerequisites
- Python 3.11+ · Node.js 18+ · Git

### 1 — Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # defaults work for local SQLite

uvicorn main:app --reload --port 8000
# API docs → http://localhost:8000/docs
```

### 2 — Create first admin user

```bash
# Still inside backend/ with venv active:
python seed_admin.py
# prompted for username / email / password

# Or pass args directly:
python seed_admin.py --username admin --email admin@example.com --password mypassword
```

### 3 — Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # VITE_API_URL can stay empty for local dev
npm run dev
# → http://localhost:5173
```

---

## Production Deployment (all free tiers)

| Layer    | Service | Free |
|----------|---------|------|
| Database | Turso   | ✅ 9 GB |
| Backend  | Render  | ✅ |
| Frontend | Vercel  | ✅ |

---

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

> Confirm `.env` and `*.db` are NOT in the commit (`git status` should not show them).

---

### Step 2 — Create Turso database

```bash
# Install Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash

turso auth login                         # opens browser

turso db create face-attendance          # create the DB

turso db show face-attendance --url      # copy this → DATABASE_URL
turso db tokens create face-attendance   # copy this → DATABASE_AUTH_TOKEN
```

Save both values — you'll paste them into Render in Step 3.

---

### Step 3 — Deploy backend on Render

1. Go to [render.com](https://render.com) → **New → Blueprint** → connect your GitHub repo.  
   Render reads `render.yaml` automatically.

2. In the service → **Environment**, add these variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `libsql://face-attendance-<org>.turso.io` |
| `DATABASE_AUTH_TOKEN` | (token from Step 2) |
| `DESKTOP_API_KEY` | any strong random string |
| `ALLOWED_ORIGINS` | `["https://your-app.vercel.app"]` ← fill after Step 4 |

3. Click **Deploy**. Wait for "Live" status.

4. Copy your backend URL → `https://face-attendance-api.onrender.com`

5. Verify:
```bash
curl https://face-attendance-api.onrender.com/health
# {"status":"ok","version":"1.0.0"}
```

> **Free tier note:** Render spins the service down after 15 min of inactivity.  
> First request after sleep takes ~30 s. This is normal on the free plan.

---

### Step 4 — Deploy frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New → Project** → import your repo.

2. Configure:
   - **Root Directory:** `frontend`
   - **Framework:** Vite (auto-detected)

3. Add environment variable:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://face-attendance-api.onrender.com` |

4. Click **Deploy**. Copy your Vercel URL.

---

### Step 5 — Update CORS on Render

Go to Render → service → **Environment** → update:

```
ALLOWED_ORIGINS=["https://face-attendance-yourname.vercel.app"]
```

Render auto-redeploys on save.

---

### Step 6 — Create admin user in production

Use the Render **Shell** tab (or curl) to seed your admin:

**Option A — Render Shell**
```bash
cd backend
python seed_admin.py --username admin --email you@example.com --password YourStrongPass
```

**Option B — curl**
```bash
curl -X POST https://face-attendance-api.onrender.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"you@example.com","password":"YourStrongPass","role":"admin"}'
```

Log in at your Vercel URL. ✅

---

### Step 7 — (Optional) Migrate local SQLite data to Turso

```bash
sqlite3 backend/attendance.db .dump > dump.sql
turso db shell face-attendance < dump.sql
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Required in prod |
|----------|-------------|-----------------|
| `DATABASE_URL` | `libsql://...` (Turso) or `file:./attendance.db` (local) | ✅ |
| `DATABASE_AUTH_TOKEN` | Turso auth token (blank for local) | ✅ |
| `SECRET_KEY` | JWT signing key — long random string | ✅ |
| `DESKTOP_API_KEY` | Static key for desktop app `/bulk` endpoint | ✅ |
| `ALLOWED_ORIGINS` | JSON list of allowed frontend origins | ✅ |
| `DEBUG` | `false` in production | ❌ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default: 60 | ❌ |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Default: 7 | ❌ |

### Frontend (`frontend/.env.local`)

| Variable | Description | Required in prod |
|----------|-------------|-----------------|
| `VITE_API_URL` | Full Render backend URL | ✅ |

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/login` | — | Login (form-encoded), returns JWT |
| POST | `/api/auth/refresh` | — | Refresh access token |
| GET | `/api/auth/me` | JWT | Current user profile |
| POST | `/api/auth/register` | — | Register user |
| GET | `/api/employees/` | JWT | List employees |
| POST | `/api/employees/` | Admin | Create employee |
| PATCH | `/api/employees/{id}` | Admin | Update employee |
| DELETE | `/api/employees/{id}` | Admin | Delete employee |
| POST | `/api/attendance/bulk` | API Key | Bulk insert from desktop |
| GET | `/api/attendance/today` | JWT | Today's summary |
| GET | `/api/attendance/date/{date}` | JWT | By date |
| GET | `/api/attendance/employee/{id}` | JWT | Employee history |
| GET | `/api/attendance/monthly/{y}/{m}` | JWT | Monthly chart data |
| GET | `/api/reports/export/csv` | JWT | Download CSV |
| GET | `/api/reports/department-summary` | JWT | Dept counts |
| GET | `/health` | — | Health check |

Interactive docs: `https://your-backend.onrender.com/docs`

---

## Troubleshooting

**`authStore` / import errors in frontend**  
→ Make sure all files from `frontend/src/store/` are present. Run `npm install` before `npm run dev`.

**Backend won't start**  
→ Check all env vars are set. Run `pip install -r requirements.txt` in the `backend/` folder.

**Login returns 422 Unprocessable Entity**  
→ FastAPI's `/api/auth/login` expects `application/x-www-form-urlencoded`, not JSON. The `authStore.js` handles this correctly.

**CORS error in browser**  
→ `ALLOWED_ORIGINS` on Render must exactly match your Vercel URL — no trailing slash.

**Slow first load on Render**  
→ Free tier cold start (~30 s). Upgrade to Starter plan for always-on.

**Turso connection error**  
→ Verify `DATABASE_URL` starts with `libsql://` and re-generate the token:  
`turso db tokens create face-attendance`
