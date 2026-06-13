from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

# CORS GLOBAL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: ["https://smart-condominium-web.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IDENTITY_URL = "http://localhost:8011"
PLATE_IDENTITY_URL = "http://localhost:8012"
BACKEND_URL = "http://localhost:8001"


def filter_headers(headers: dict) -> dict:
    """Quita headers que rompen CORS en proxys"""
    excluded = {
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "upgrade",
        "host",
    }
    return {k: v for k, v in headers.items() if k.lower() not in excluded}


@app.api_route(
    "/identity/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def identity_proxy(path: str, request: Request):

    if request.method == "OPTIONS":
        return Response(status_code=204)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{IDENTITY_URL}/{path}",
            headers=filter_headers(dict(request.headers)),
            content=await request.body(),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filter_headers(dict(resp.headers)),
    )


@app.api_route(
    "/plate-identity/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def plate_identity_proxy(path: str, request: Request):

    if request.method == "OPTIONS":
        return Response(status_code=204)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{PLATE_IDENTITY_URL}/{path}",
            headers=filter_headers(dict(request.headers)),
            content=await request.body(),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filter_headers(dict(resp.headers)),
    )


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def backend_proxy(path: str, request: Request):
    """Proxy para el backend Django principal"""
    
    if request.method == "OPTIONS":
        return Response(status_code=204)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{BACKEND_URL}/api/{path}",
            headers=filter_headers(dict(request.headers)),
            content=await request.body(),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filter_headers(dict(resp.headers)),
    )
