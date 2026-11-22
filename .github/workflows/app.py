
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pathlib import Path
from processor import process_photo, process_video
import tempfile
import os

app = FastAPI()

API_KEY = os.environ.get("PROCESSOR_API_KEY")


@app.get("/")
def home():
    return {"status": "Daniel Sticker Processor is running"}


@app.post("/photo")
async def photo(
    file: UploadFile = File(...),
    x_api_key: str = Header(...)
):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Unsupported image")

    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"

    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / f"input{suffix}"
        output = Path(temp) / "sticker.png"

        source.write_bytes(await file.read())
        process_photo(source, output)

        return {
            "filename": "sticker.png",
            "data": output.read_bytes().hex()
        }


@app.post("/video")
async def video(
    file: UploadFile = File(...),
    x_api_key: str = Header(...)
):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if file.content_type not in ("video/mp4", "video/webm", "video/quicktime"):
        raise HTTPException(status_code=400, detail="Unsupported video")

    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / "input.mp4"
        output = Path(temp) / "sticker.webm"

        source.write_bytes(await file.read())
        process_video(source, output)

        return {
            "filename": "sticker.webm",
            "data": output.read_bytes().hex()
        }
