import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Response
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PUBLIC_BUCKET = os.getenv("PUBLIC_BUCKET")
if not PUBLIC_BUCKET:
    raise RuntimeError("Missing PUBLIC_BUCKET environment variable")

storage_client = storage.Client()
bucket = storage_client.bucket(PUBLIC_BUCKET)

app = FastAPI()


@app.middleware("http")
async def extract_subdomain(request: Request, call_next):
    host = request.headers.get("host", "")
    host = host.split(":")[0]
    logger.info(f"Host (no port): {host}")

    parts = host.split(".")
    if len(parts) == 2 and parts[-1] == "localhost":
        # e.g. foo.localhost → parts = ['foo', 'localhost']
        request.state.subdomain = parts[0]
    elif len(parts) >= 3:
        request.state.subdomain = parts[0]
    else:
        request.state.subdomain = None

    response = await call_next(request)
    return response


@app.get("/{path:path}")
async def serve_file(request: Request, path: str = ""):
    subdomain = request.state.subdomain
    if not subdomain:
        raise HTTPException(status_code=400, detail="Missing subdomain")

    blob_path = f"{subdomain}/{path or 'index.html'}"
    blob = bucket.blob(blob_path)

    if not blob.exists():
        raise HTTPException(status_code=404, detail="File not found")

    blob.reload()

    content_type = blob.content_type or "application/octet-stream"
    data = blob.download_as_bytes()

    return Response(content=data, media_type=content_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
