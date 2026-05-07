import os
import uuid
import glob
import time
import threading

import imageio_ffmpeg
import yt_dlp
from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", os.path.join("/tmp", "downloads"))
JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", 60 * 60))
FFMPEG_LOCATION = os.environ.get("FFMPEG_LOCATION") or imageio_ffmpeg.get_ffmpeg_exe()
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}
jobs_lock = threading.Lock()


def cleanup_old_jobs():
    cutoff = time.time() - JOB_TTL_SECONDS
    with jobs_lock:
        expired = [
            job_id for job_id, job in jobs.items()
            if job.get("created_at", cutoff) < cutoff
        ]
        expired_files = [jobs[job_id].get("file") for job_id in expired]
        for job_id in expired:
            jobs.pop(job_id, None)

    for path in expired_files:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass


def update_job(job_id, **values):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(values)


def get_json_body():
    return request.get_json(silent=True) or {}


def run_download(job_id, url, format_choice, format_id):
    job = jobs[job_id]
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "noplaylist": True,
        "outtmpl": out_template,
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "socket_timeout": 300,  # 5 min limit per network operation
        "ffmpeg_location": FFMPEG_LOCATION,
    }

    if format_choice == "audio":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }]
    elif format_id:
        ydl_opts["format"] = f"{format_id}+bestaudio/best"
        ydl_opts["merge_output_format"] = "mp4"
    else:
        ydl_opts["format"] = "bestvideo+bestaudio/best"
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{job_id}.*"))
        if not files:
            update_job(
                job_id,
                status="error",
                error="Download completed but no file was found",
            )
            return

        if format_choice == "audio":
            target = [f for f in files if f.endswith(".mp3")]
            chosen = target[0] if target else files[0]
        else:
            target = [f for f in files if f.endswith(".mp4")]
            chosen = target[0] if target else files[0]

        for f in files:
            if f != chosen:
                try:
                    os.remove(f)
                except OSError:
                    pass

        ext = os.path.splitext(chosen)[1]
        title = job.get("title", "").strip()
        if title:
            safe_title = "".join(c for c in title if c not in r'\/:*?"<>|').strip()[:80].strip()
            filename = f"{safe_title}{ext}" if safe_title else os.path.basename(chosen)
        else:
            filename = os.path.basename(chosen)

        update_job(job_id, status="done", file=chosen, filename=filename)
    except yt_dlp.utils.DownloadError as e:
        update_job(job_id, status="error", error=str(e).strip().split("\n")[-1])
    except Exception:
        update_job(job_id, status="error", error="Download failed")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/api/info", methods=["POST"])
def get_info():
    cleanup_old_jobs()
    data = get_json_body()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "socket_timeout": 60,  # 1 min limit for metadata fetch
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Build quality options — keep best format per resolution
        best_by_height = {}
        for f in info.get("formats", []):
            height = f.get("height")
            if height and f.get("vcodec", "none") != "none":
                tbr = f.get("tbr") or 0
                if height not in best_by_height or tbr > (best_by_height[height].get("tbr") or 0):
                    best_by_height[height] = f

        formats = []
        for height, f in best_by_height.items():
            formats.append({
                "id": f["format_id"],
                "label": f"{height}p",
                "height": height,
            })
        formats.sort(key=lambda x: x["height"], reverse=True)

        return jsonify({
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration"),
            "uploader": info.get("uploader", ""),
            "formats": formats,
        })
    except yt_dlp.utils.DownloadError:
        return jsonify({"error": "Could not fetch video info"}), 400
    except Exception:
        return jsonify({"error": "Could not fetch video info"}), 400


@app.route("/api/download", methods=["POST"])
def start_download():
    cleanup_old_jobs()
    data = get_json_body()
    url = data.get("url", "").strip()
    format_choice = data.get("format", "video")
    format_id = data.get("format_id")
    title = data.get("title", "")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {
            "status": "downloading",
            "url": url,
            "title": title,
            "created_at": time.time(),
        }

    thread = threading.Thread(target=run_download, args=(job_id, url, format_choice, format_id))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def check_status(job_id):
    cleanup_old_jobs()
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "error": job.get("error"),
        "filename": job.get("filename"),
    })


@app.route("/api/file/<job_id>")
def download_file(job_id):
    cleanup_old_jobs()
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "File not ready"}), 404
    return send_file(job["file"], as_attachment=True, download_name=job["filename"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8899))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port)
