from fastapi import FastAPI
from app.api.auth import router as auth_router

app = FastAPI(title="AI Knowledge Assistant")

app.include_router(auth_router)


@app.get("/")
def home():
    return {"message": "Hello, AI Knowledge Assistant!"}