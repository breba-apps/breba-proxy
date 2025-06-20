from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI()


@app.middleware("http")
async def extract_subdomain(request: Request, call_next):
    host = request.headers.get("host", "")
    host = host.split(":")[0]
    print(f"Host (no port): {host}")

    parts = host.split(".")
    if len(parts) == 2 and parts[-1] == "localhost":
        # e.g. foo.localhost → parts = ['foo', 'localhost']
        request.state.subdomain = parts[0]
    elif len(parts) == 3:
        request.state.subdomain = parts[0]
    else:
        request.state.subdomain = None

    response = await call_next(request)
    return response


@app.get("/")
async def root(request: Request):
    subdomain = request.state.subdomain
    if subdomain:
        return PlainTextResponse(f"Hello from {subdomain}")
    else:
        return PlainTextResponse("Hello, no subdomain")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)