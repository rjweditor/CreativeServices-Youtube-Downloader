# YT Grabber 🎬

A simple web app to download YouTube videos as MP4 files.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

---

## How to Run

### First time setup

1. Open a terminal (Mac: Spotlight → "Terminal" / Windows: Start → "Command Prompt")
2. Navigate to this folder:
   ```
   cd path/to/this/folder
   ```
3. Start the app:
   ```
   docker compose up --build
   ```
4. Open your browser and go to: **http://localhost:5000**

### Next time (already built)

```
docker compose up
```

### To stop the app

Press `Ctrl + C` in the terminal, then run:
```
docker compose down
```

---

## How to Use

1. Copy any YouTube video URL
2. Paste it into the box on the page
3. Click **GRAB**
4. Wait for the download to finish
5. Click **Download MP4** to save the file

---

## Notes

- Downloads are saved temporarily inside the container and served via the browser
- A `downloads/` folder will appear next to this file with your videos
- For personal use only — respect copyright and YouTube's Terms of Service
