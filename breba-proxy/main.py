import logging
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PUBLIC_BUCKET = os.getenv("PUBLIC_BUCKET")
CLOUDFLARE_ENDPOINT = os.getenv("CLOUDFLARE_ENDPOINT")

if not PUBLIC_BUCKET:
    raise RuntimeError("Missing PUBLIC_BUCKET environment variable")
if not CLOUDFLARE_ENDPOINT:
    raise RuntimeError("Missing CLOUDFLARE_ENDPOINT environment variable")

# R2 uses "auto" region; SigV4 works. Some setups prefer 's3v4' explicit signature.
boto_cfg = Config(
    region_name="auto",
    retries={"max_attempts": 3, "mode": "standard"},
    s3={"addressing_style": "virtual"}
)

session = boto3.session.Session()
s3_client = session.client(
    service_name="s3",
    endpoint_url=CLOUDFLARE_ENDPOINT,
    config=boto_cfg,
)


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

    key = f"{subdomain}/{path or 'index.html'}"

    try:
        obj = s3_client.get_object(Bucket=PUBLIC_BUCKET, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "NotFound", "404"):
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=502, detail="Storage backend error")

    data = obj["Body"].read()
    content_type = obj.get("ContentType") or "application/octet-stream"

    return Response(content=data, media_type=content_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
