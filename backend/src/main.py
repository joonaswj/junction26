from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from junction26.data.routes import router as data_router

app = FastAPI()
app.include_router(data_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI!"}

