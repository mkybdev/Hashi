# Project Overview: Japanese Pitch Accent Game (8-bit)

This project is a web-based game where players must guess words that share the same pitch accent as a given target word.

## Technology Stack

- **Monorepo Structure**: Managed by `bun` (where applicable for JS).
- **Frontend**:
  - **Framework**: Vite + React
  - **Hosting**: Firebase Hosting
  - **UI Library**: `TheOrcDev/8bitcn-ui` (Shadcn/ui based 8-bit aesthetic)
  - **Package Manager**: `bun`
- **Backend**:
  - **Runtime**: Python 3.10+
  - **Framework**: FastAPI (Lightweight, fast)
  - **Inference**: `PKSHATechnology-Research/tdmelodic` (Accent estimation)
  - **Morphological Analysis**: `sudachipy` (if needed by tdmelodic)
  - **Infrastructure**: Google Cloud Run (Serverless, Free Tier eligible)
- **Infrastructure / DevOps**:
  - **Platform**: GCP (Google Cloud Platform)
  - **Gateway**: Firebase Hosting (Rewrites to Cloud Run)

## Monorepo Structure

```
.
├── packages/
│   ├── frontend/       # Vite + React app
│   └── backend/        # FastAPI + tdmelodic app
├── firebase.json       # Firebase configuration (Hosting + Rewrites)
├── bun.lockb
└── package.json        # Root scripts
```

## Game Mechanics

1.  **Target Word**: The game presents a "Target Word" (randomly selected or daily).
2.  **Input**: Use inputs a Japanese word (Hiragana/Kanji).
3.  **Process**:
    -   Frontend sends input to Backend.
    -   Backend converts input to "Reading" and "Accent Pattern" using `tdmelodic`.
    -   Backend compares with Target Word's accent.
4.  **Feedback**:
    -   Success: 8-bit victory sound/visual.
    -   Fail: Show the accent difference (visualize high/low pitch).

## Development Setup

-   **Frontend**: `bun run dev` (in `packages/frontend`)
-   **Backend**: `uvicorn main:app --reload` (in `packages/backend`)
