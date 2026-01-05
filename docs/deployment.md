# Deployment Guide

This guide describes how to deploy the Hashi application.
We recommend using **Google Cloud Run** for the backend and **Vercel** for the frontend.

## Prerequisites

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth login`)
- A GitHub repository with this project pushed

---

## 1. Backend Deployment (Google Cloud Run)

The backend is a FastAPI application running in a Docker container.

### Fast Deployment (using Source)

1. Open your terminal and navigate to the backend directory:
   ```bash
   cd packages/backend
   ```

2. Run the deploy command:
   ```bash
   gcloud run deploy hashi-backend \
     --source . \
     --region asia-northeast1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2
   ```
   *Note: Using `--memory 2Gi` is recommended because the application loads machine learning models (tdmelodic) and dictionaries.*
   - If prompted to enable APIs (like Cloud Build, Cloud Run), say `y` (yes).
   - This command zips the current directory, builds the Docker container in the cloud, and deploys it.

3. **Get the Backend URL:**
   Once finished, it will display a Service URL, e.g.:
   `https://hashi-backend-xyz123-an.a.run.app`

   > **Note:** This URL is your API base. The actual API endpoints are at `/api/...`.

---

## 2. Frontend Deployment (Vercel)

The frontend is a React application built with Vite.

1. **Push your code** to GitHub.
2. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New..."** -> **"Project"**.
3. Import your implementation repository.
4. **Configure Project:**
   - **Framework Preset:** Vite
   - **Root Directory:** Click "Edit" and select `packages/frontend`.
5. **Environment Variables:**
   - Expand the "Environment Variables" section.
   - Add a new variable:
     - **Name:** `VITE_API_URL`
     - **Value:** `YOUR_BACKEND_URL/api`  
       (e.g., `https://hashi-backend-xyz123-an.a.run.app/api`)
       *Don't forget the `/api` at the end!*
6. Click **"Deploy"**.

---

## Verification

1. Open your Vercel deployment URL.
2. The game should load.
3. Check the "Network" tab in Developer Tools. You should see requests to your Cloud Run URL (e.g., `.../api/target-word`).
4. If requests succeed, deployment is complete!

## Troubleshooting

- **CORS Errors:** Ensure the Backend is deployed with the latest code containing the CORS configuration in `main.py`.
- **404 on API calls:** Check if you included `/api` in the `VITE_API_URL` environment variable.
