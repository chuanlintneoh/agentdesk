from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os
from tools import mcp
from api import register_agent_routes

mcp_app = mcp.http_app(path="/")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with mcp_app.lifespan(app):
        yield

app = FastAPI(
    title="AgentDesk Core API",
    description="Asynchronous backend orchestrating autonomous tool-calling loops.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"], # Allows headers like Content-Type
)

@app.middleware("http")
async def mcp_token_middleware(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        token = request.headers.get("x-mcp-token")
        expected_token = os.getenv("MCP_SECRET_TOKEN", "secret-token-default")
        
        if not token or token != expected_token:
            return JSONResponse(
                status_code=403, 
                content={"detail": "Invalid or missing X-MCP-Token header."}
            )
    return await call_next(request)

app.mount("/mcp", mcp_app)

register_agent_routes(app)