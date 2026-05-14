from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import csv
import os

app = FastAPI()

# File to store our 500+ scans
DATA_FILE = "web_scans.csv"

# Ensure CSV exists with headers
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "URL"])

@app.get("/", response_class=HTMLResponse)
async def index():
    # We embed the HTML/JS directly for a single-file deployment
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pro QR Batch Scanner</title>
        <script src="https://unpkg.com/html5-qrcode"></script>
        <style>
            body { font-family: sans-serif; text-align: center; background: #121212; color: white; }
            #reader { width: 100%; max-width: 500px; margin: auto; border: 2px solid #333; }
            #stats { margin: 20px; font-size: 1.2rem; color: #00ff00; }
            .log { height: 200px; overflow-y: scroll; background: #1e1e1e; padding: 10px; margin: 10px; }
        </style>
    </head>
    <body>
        <h2>High-Speed Batch Scanner</h2>
        <div id="stats">Scanned: <span id="count">0</span>/500</div>
        <div id="reader"></div>
        <div class="log" id="log">--- Results will appear here ---</div>

        <script>
            const scannedUrls = new Set();
            const logElement = document.getElementById('log');
            const countElement = document.getElementById('count');

            function onScanSuccess(decodedText) {
                if (!scannedUrls.has(decodedText)) {
                    scannedUrls.add(decodedText);
                    
                    // Update UI
                    countElement.innerText = scannedUrls.size;
                    const entry = document.createElement('div');
                    entry.innerText = `[OK] ${decodedText}`;
                    logElement.prepend(entry);

                    // Send to Python Backend silently
                    fetch('/log-scan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: decodedText })
                    });

                    // Haptic feedback (vibration) for speed confirmation
                    if (navigator.vibrate) navigator.vibrate(50);
                }
            }

            const html5QrcodeScanner = new Html5Qrcode("reader");
            html5QrcodeScanner.start(
                { facingMode: "environment" }, 
                { fps: 20, qrbox: { width: 250, height: 250 } },
                onScanSuccess
            );
        </script>
    </body>
    </html>
    """

@app.post("/log-scan")
async def log_scan(request: Request):
    data = await request.json()
    url = data.get("url")
    import datetime
    with open(DATA_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.datetime.now(), url])
    return {"status": "logged"}