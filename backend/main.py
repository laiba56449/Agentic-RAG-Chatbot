from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.organizations import router as organizations_router
from app.api.document import router as documents_router, personal_router

app = FastAPI(title="AI Knowledge Assistant")

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(documents_router)
app.include_router(personal_router)


@app.get("/")
def home():
    return {"message": "Hello, AI Knowledge Assistant!"}