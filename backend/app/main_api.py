"""
Main entry point for the FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="TG Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

def main():
    import uvicorn

    uvicorn.run(
        "app.main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.api_reload,
    )

if __name__ == "__main__":
    main()
