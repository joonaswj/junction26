from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from junction26.app_routes import router as app_router
from junction26.data.routes import router as data_router

app = FastAPI(title="S-Pankki assistant API")
app.include_router(app_router)
app.include_router(data_router)

app.add_middleware(
    CORSMiddleware,
    # Vite dev server and Expo web. Native apps on a phone don't need CORS.
    allow_origins=["http://localhost:5173", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI!"}

