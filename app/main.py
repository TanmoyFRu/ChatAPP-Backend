from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
import time
import logging
from app.core.config import settings
from app.database import engine, Base
from app.routes import auth, rooms, chat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app with Bearer Token security scheme in docs
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="A chat API with AI integration using Gemini",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(chat.router)

# Legacy routes
@app.post("/signup")
async def signup_legacy(request: Request):
    return JSONResponse(
        status_code=301,
        content={"message": "Use /auth/signup instead"},
        headers={"Location": "/auth/signup"}
    )

@app.post("/login")
async def login_legacy(request: Request):
    return JSONResponse(
        status_code=301,
        content={"message": "Use /auth/login instead"},
        headers={"Location": "/auth/login"}
    )

@app.post("/room")
async def create_room_legacy(request: Request):
    return JSONResponse(
        status_code=301,
        content={"message": "Use /rooms/ instead"},
        headers={"Location": "/rooms/"}
    )

@app.get("/room/{room_id}")
async def get_room_legacy(room_id: str):
    return JSONResponse(
        status_code=301,
        content={"message": f"Use /rooms/{room_id} instead"},
        headers={"Location": f"/rooms/{room_id}"}
    )

@app.get("/all_room")
async def get_all_rooms_legacy():
    return JSONResponse(
        status_code=301,
        content={"message": "Use /rooms/ instead"},
        headers={"Location": "/rooms/"}
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": f"{settings.APP_NAME} is running",
        "version": settings.VERSION
    }

# Custom OpenAPI schema so "Authorize" asks for Bearer token
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="A chat API with AI integration using Gemini",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    # Apply BearerAuth globally
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
