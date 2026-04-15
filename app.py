from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import threading
import uuid
import time

app = Flask(__name__)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

def run_download(job_id, url):
    jobs[job_id]["status"] = "downloading"
    jobs[job_id]["progress"] = 0

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                jobs[job_id]["progress"] = int(downloaded / total * 90)
            jobs[job_id]["speed"] = d.get("_speed_str", "")
            jobs[job_id]["eta"] = d.get("_eta_str", "")
        elif d["status"] == "finished":
            jobs[job_id]["progress"] = 95

    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}_%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
            jobs[job_id]["title"] = title

        # Find the downloaded file
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(job_id):
                jobs[job_id]["filename"] = f
                jobs[job_id]["filepath"] = os.path.join(DOWNLOAD_DIR, f)
                break

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YT Grabber</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0a0a0a;
    --surface: #111111;
    --border: #1e1e1e;
    --accent: #ff4d00;
    --accent2: #ff8c42;
    --text: #f0f0f0;
    --muted: #555;
    --success: #00e676;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    overflow-x: hidden;
  }

  body::before {
    content: '';
    position: fixed;
    top: -40%;
    left: 50%;
    transform: translateX(-50%);
    width: 700px;
    height: 700px;
    background: radial-gradient(circle, rgba(255,77,0,0.08) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }

  .container {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 620px;
  }

  header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(3.5rem, 10vw, 5.5rem);
    letter-spacing: 0.04em;
    line-height: 1;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .tagline {
    color: var(--muted);
    font-size: 0.85rem;
    font-weight: 300;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.25rem;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2rem;
  }

  .input-group {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }

  input[type="text"] {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s;
  }

  input[type="text"]:focus {
    border-color: var(--accent);
  }

  input[type="text"]::placeholder { color: var(--muted); }

  button.grab-btn {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 0.9rem 1.5rem;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
    white-space: nowrap;
  }

  button.grab-btn:hover { background: #e04300; }
  button.grab-btn:active { transform: scale(0.97); }
  button.grab-btn:disabled { background: var(--muted); cursor: not-allowed; transform: none; }

  /* Progress */
  #status-area { display: none; }

  .status-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    color: var(--muted);
    margin-bottom: 0.6rem;
  }

  .status-label .state { color: var(--text); font-weight: 500; }

  .progress-track {
    background: var(--border);
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
  }

  .progress-bar {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    width: 0%;
    transition: width 0.4s ease;
  }

  .meta {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.5rem;
    min-height: 1.2em;
  }

  /* Download button */
  #download-area { display: none; margin-top: 1.5rem; }

  .download-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    width: 100%;
    background: transparent;
    border: 1.5px solid var(--success);
    color: var(--success);
    border-radius: 10px;
    padding: 1rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.2s, color 0.2s;
  }

  .download-btn:hover {
    background: var(--success);
    color: #000;
  }

  .download-btn svg { flex-shrink: 0; }

  /* Error */
  #error-area {
    display: none;
    margin-top: 1rem;
    padding: 0.8rem 1rem;
    background: rgba(255,50,50,0.08);
    border: 1px solid rgba(255,50,50,0.25);
    border-radius: 8px;
    color: #ff6b6b;
    font-size: 0.85rem;
  }

  .divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
  }

  .tips {
    font-size: 0.78rem;
    color: var(--muted);
    line-height: 1.7;
  }

  .tips span { color: var(--accent2); }

  footer {
    margin-top: 2rem;
    text-align: center;
    font-size: 0.75rem;
    color: #333;
  }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo">YT GRABBER</div>
    <div class="tagline">Paste · Grab · Download</div>
  </header>

  <div class="card">
    <div class="input-group">
      <input type="text" id="url-input" placeholder="Paste a YouTube URL here…" />
      <button class="grab-btn" id="grab-btn" onclick="startDownload()">GRAB</button>
    </div>

    <div id="status-area">
      <div class="status-label">
        <span class="state" id="state-text">Starting…</span>
        <span id="pct-text">0%</span>
      </div>
      <div class="progress-track">
        <div class="progress-bar" id="progress-bar"></div>
      </div>
      <div class="meta" id="meta-text"></div>
    </div>

    <div id="download-area">
      <a class="download-btn" id="download-link" href="#" download>
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M12 5v14M5 12l7 7 7-7"/><rect x="3" y="19" width="18" height="2" rx="1" fill="currentColor" stroke="none"/>
        </svg>
        Download MP4
      </a>
    </div>

    <div id="error-area"></div>

    <hr class="divider">
    <div class="tips">
      <span>✦</span> Works with any public YouTube video &nbsp;·&nbsp;
      <span>✦</span> Downloads as MP4 &nbsp;·&nbsp;
      <span>✦</span> Best available quality
    </div>
  </div>

  <footer>For personal use only · Respect copyright</footer>
</div>

<script>
  let pollTimer = null;

  async function startDownload() {
    const url = document.getElementById('url-input').value.trim();
    if (!url) { alert('Please paste a YouTube URL first.'); return; }

    document.getElementById('grab-btn').disabled = true;
    document.getElementById('status-area').style.display = 'block';
    document.getElementById('download-area').style.display = 'none';
    document.getElementById('error-area').style.display = 'none';
    setProgress(0, 'Starting…', '');

    try {
      const res = await fetch('/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      if (data.job_id) pollStatus(data.job_id);
      else showError(data.error || 'Failed to start download.');
    } catch(e) { showError('Server error: ' + e.message); }
  }

  function pollStatus(jobId) {
    pollTimer = setInterval(async () => {
      try {
        const res = await fetch('/status/' + jobId);
        const d = await res.json();

        if (d.status === 'downloading') {
          const meta = [d.speed, d.eta ? 'ETA ' + d.eta : ''].filter(Boolean).join(' · ');
          setProgress(d.progress, 'Downloading…', meta);
        } else if (d.status === 'done') {
          clearInterval(pollTimer);
          setProgress(100, 'Done!', d.title || '');
          showDownload(jobId, d.filename);
        } else if (d.status === 'error') {
          clearInterval(pollTimer);
          showError(d.error);
        }
      } catch(e) { /* retry */ }
    }, 800);
  }

  function setProgress(pct, state, meta) {
    document.getElementById('progress-bar').style.width = pct + '%';
    document.getElementById('pct-text').textContent = pct + '%';
    document.getElementById('state-text').textContent = state;
    document.getElementById('meta-text').textContent = meta;
  }

  function showDownload(jobId, filename) {
    const area = document.getElementById('download-area');
    const link = document.getElementById('download-link');
    link.href = '/download/' + jobId;
    link.textContent = '';
    link.innerHTML = `<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12l7 7 7-7"/><rect x="3" y="19" width="18" height="2" rx="1" fill="currentColor" stroke="none"/></svg> Download MP4`;
    area.style.display = 'block';
    document.getElementById('grab-btn').disabled = false;
  }

  function showError(msg) {
    const el = document.getElementById('error-area');
    el.textContent = '⚠ ' + msg;
    el.style.display = 'block';
    document.getElementById('grab-btn').disabled = false;
  }

  document.getElementById('url-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') startDownload();
  });
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": 0, "speed": "", "eta": "", "title": "", "filename": None}

    t = threading.Thread(target=run_download, args=(job_id, url), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("filepath"):
        return "File not found", 404
    return send_file(job["filepath"], as_attachment=True, download_name=job.get("filename", "video.mp4"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
