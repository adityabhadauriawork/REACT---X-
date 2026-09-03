# REACT-X Deployment & Operations Runbook

**Document Version:** 1.0.0  
**Phase:** 22 — Final External Integration, Deployment & Release  

---

## 1. System Prerequisites

- **Python:** 3.12.x or later
- **Node.js:** 18.x or later (npm 9+)
- **Operating System:** Linux (Ubuntu 22.04+), Windows Server, or macOS
- **Hardware:** 4+ CPU Cores, 8 GB RAM, 20 GB Disk (for SQLite / PostgreSQL local storage)

---

## 2. Environment Configuration (`.env`)

Create `backend/.env` containing:
```ini
# Core Configuration
PROJECT_NAME="REACT-X"
API_V1_STR="/api"
SECRET_KEY="generate-secure-production-key-here"

# Database Configuration
DATABASE_URL="sqlite:///./reactx_production.db"
# Or PostgreSQL: DATABASE_URL="postgresql://user:password@localhost:5432/reactx"

# External API Keys (Optional for live satellite ingestion)
FIRMS_MAP_KEY=""
MOSDAC_TOKEN=""

# CORS Origins
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
```

---

## 3. Clean-Start & Initialization

### Backend Setup:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Build & Serve:
```bash
cd frontend
npm install
npm run build
```
The compiled single-page application is written to `frontend/dist/`.

---

## 4. Health & Readiness Verification

- **System Readiness Endpoint:**
  ```bash
  curl -X GET http://127.0.0.1:8000/api/orchestration/readiness
  ```
  Expected Response: `{"status": "READY", "database_connected": true, ...}`
- **Telemetry Ingestion Health:**
  ```bash
  curl -X GET http://127.0.0.1:8000/api/telemetry/health
  ```
  Expected Response: `{"status": "HEALTHY", "active_sensors": 4, ...}`

---

## 5. Backup & Disaster Recovery

- **Database Backup:**
  ```bash
  sqlite3 reactx_production.db ".backup 'backup_$(date +%Y%m%d).db'"
  ```
- **Restoration:**
  ```bash
  cp backup_20260901.db reactx_production.db
  ```
