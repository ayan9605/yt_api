from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import yt_dlp
import os
import uuid
import shutil
import asyncio

app = FastAPI(title="YouTube Video Downloader API")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def run_yt_dlp(url: str, output_template: str) -> str:
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    filename = ydl.prepare_filename(info)
    # Force rename to .mp4 if not already
    if not filename.endswith('.mp4'):
        base = os.path.splitext(filename)[0]
        new_filename = base + ".mp4"
        shutil.move(filename, new_filename)
        filename = new_filename
    return filename

@app.post("/download/")
async def download_video(url: str = Query(..., example="https://www.youtube.com/watch?v=dQw4w9WgXcQ")):
    """
    Download video from YouTube URL as an MP4 and return the filename.
    """
    video_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    try:
        # Run yt-dlp in thread to avoid blocking event loop
        filename = await asyncio.to_thread(run_yt_dlp, url, output_template)
        return {"filename": os.path.basename(filename)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

@app.get("/files/{filename}")
async def get_file(filename: str):
    """
    Serve the previously downloaded MP4 video file.
    """
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="video/mp4", filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/")
async def health_check():
    return {"status": "YouTube Video Downloader API running"}

# Run using:
# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
