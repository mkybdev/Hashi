# Walkthrough: Japanese Pitch Accent Game (8-bit)

This project provides an 8-bit styled Japanese pitch accent game using `tdmelodic` for accent estimation.

## Project Structure

- **packages/frontend**: React + Vite + Shadcn UI (8-bit customized)
- **packages/backend**: Python FastAPI + tdmelodic (Accent Analysis API)

## Prerequisites

- Node.js (v20+)
- Python (3.10+)
- Google Cloud SDK (for deployment)
- Firebase CLI (for deployment)

## Local Development

### 1. Backend

```bash
cd packages/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Run server (default port 8000)
uvicorn main:app --reload --port 8000
```

Verify: `curl -X POST http://localhost:8000/api/analyze -d '{"text": "箸"}' -H "Content-Type: application/json"`

### 2. Frontend

```bash
cd packages/frontend
npm install
npm run dev
```

Open `http://localhost:5173`.
The frontend proxies `/api` requests to `http://localhost:8000`.

## Deployment

### 1. Backend (Cloud Run)

Building and deploying the container to Google Cloud Run.

```bash
cd packages/backend
# Build using Cloud Build or locally
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hashi-backend

# Deploy to Cloud Run
gcloud run deploy hashi-backend \
  --image gcr.io/YOUR_PROJECT_ID/hashi-backend \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

Note the Service URL (e.g., `https://hashi-backend-xyz.a.run.app`).

### 2. Frontend (Firebase Hosting)

Update `firebase.json` if your service name differs.

```bash
# In root
firebase init hosting
# (Select "dist" as public directory if asked, or verify firebase.json points to "packages/frontend/dist")

# Update firebase.json rewrites "serviceId" to match your Cloud Run service name ("hashi-backend").

# Build frontend
cd packages/frontend
npm run build

# Deploy
firebase deploy --only hosting
```

## Features

- **8-bit UI**: Using DotGothic16 font, thick borders, and non-rounded corners.
- **Accent Visualization**: Displays pitch accent pattern (H/L) derived from `tdmelodic`.
- **Game Logic**: Random target word selection (Hashi, Ame, Sora, etc.).

## Notes

- `tdmelodic` model is downloaded automatically on first run.
- `unidic` dictionary is downloaded during Docker build.
