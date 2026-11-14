import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from junction26.app_routes import router as app_router
from junction26.data.routes import router as data_router

app = FastAPI(title="S-Pankki assistant API")
app.include_router(app_router)
app.include_router(data_router)

app.add_middleware(
    CORSMiddleware,
    # Vite dev server and Expo web. Native apps on a phone don't need CORS.
    allow_origins=["http://localhost:5173", "http://localhost:8081"],
    # Also allow the app opened on a phone via the laptop's local IP.
    allow_origin_regex=r"http://(127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the built frontend (frontend/dist) from the same address as the API,
# so the whole app is one URL. Build it first: `cd frontend && npm run build`.
# Mounted last, so the API routes above take precedence.
FRONTEND_DIST = Path(
    os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")
)
if (FRONTEND_DIST / "index.html").is_file():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:

    @app.get("/")
    async def root():
        return {
            "message": "API is running. Build the frontend (cd frontend && npm run build) "
            "to serve the app here too."
        }

