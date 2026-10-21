from fastapi import FastAPI

from src.auth.router import router as auth_router

app = FastAPI(title="Secret Delivery")

app.include_router(auth_router)
