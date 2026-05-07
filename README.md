# ReClip

A self-hosted, open-source video and audio downloader with a clean web UI. Paste links from YouTube, TikTok, Instagram, Twitter/X, and 1000+ other sites, then download as MP4 or MP3.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

https://github.com/user-attachments/assets/419d3e50-c933-444b-8cab-a9724986ba05

![ReClip MP3 Mode](assets/preview-mp3.png)

## Features

- Download videos from 1000+ supported sites with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- MP4 video or MP3 audio extraction
- Bundled ffmpeg fallback for local Python installs
- Quality/resolution picker
- Bulk downloads by pasting multiple URLs at once
- Automatic URL deduplication
- Clean, responsive UI with no frontend build step

## Quick Start

### Windows

```powershell
.\reclip.ps1
```

Open http://localhost:8899.

### macOS/Linux

```bash
./reclip.sh
```

Open http://localhost:8899.

### Docker

```bash
docker build -t reclip .
docker run -p 8899:8899 reclip
```

Open http://localhost:8899.

## Usage

1. Paste one or more video URLs into the input box.
2. Choose MP4 for video or MP3 for audio.
3. Click Fetch to load video info and thumbnails.
4. Select quality/resolution if available.
5. Click Download on individual videos, or Download All.

## Hosting

ReClip is best hosted as a long-running Docker web service because downloads can take time, need ffmpeg, and temporarily store files before the browser saves them.

Recommended options:

- Render, Railway, Fly.io, or a VPS with Docker.
- Avoid serverless-only deployments for real use. Platforms such as Vercel can run Flask endpoints, but background downloads, ffmpeg work, and temporary files are a poor fit for serverless execution limits.

### Render Blueprint

This repo includes `render.yaml`, so you can deploy it as a Docker web service from GitHub:

1. Push the repo to GitHub.
2. In Render, create a new Blueprint or Web Service from this repository.
3. Select the Docker environment if prompted.
4. Deploy. Render will use `/healthz` for health checks.

The included blueprint uses Render's free web service plan for testing. If you use this often, upgrade the service to a paid always-on instance to avoid cold starts.

### Generic Docker Host

```bash
docker build -t reclip .
docker run -d --name reclip -p 8899:8899 --restart unless-stopped reclip
```

Then point your domain or reverse proxy at port 8899.

## Supported Sites

Anything [yt-dlp supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), including YouTube, TikTok, Instagram, Twitter/X, Reddit, Facebook, Vimeo, Twitch, Dailymotion, SoundCloud, Loom, Streamable, Pinterest, Tumblr, Threads, LinkedIn, and many more.

## Stack

- Backend: Python + Flask
- Frontend: Vanilla HTML/CSS/JS
- Download engine: yt-dlp + ffmpeg

## Disclaimer

This tool is intended for personal use only. Please respect copyright laws and the terms of service of the platforms you download from. The developers are not responsible for any misuse of this tool.

## License

[MIT](LICENSE)
