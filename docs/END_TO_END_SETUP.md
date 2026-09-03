# REACT-X End-to-End Setup & Deployment Guide

**Document Version:** 1.0.0  
**Phase:** 19 — End-to-End System Integration, Connectivity & Operational Orchestration  

---

## 1. Prerequisites & Environment Setup

- **Python:** 3.11+ / 3.12+
- **Node.js:** v18+ / v20+
- **Database:** SQLite (default for development/embedded) or PostgreSQL + PostGIS (production)

---

## 2. Starting Backend Services

```bash
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start FastAPI Application with Live Reload
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 3. Starting Frontend UI

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start Vite Development Server
npm run dev

# 4. Build Production Bundle
npm run build
```

---

## 4. Operational Health & Readiness Verification

- **Liveness Check:** `GET http://127.0.0.1:8000/api/health`
- **Readiness Check:** `GET http://127.0.0.1:8000/api/orchestration/readiness`
- **National Coverage Check:** `GET http://127.0.0.1:8000/api/national/coverage`
- **Execute End-to-End Pipeline:** `POST http://127.0.0.1:8000/api/orchestration/pipeline/execute`
