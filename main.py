from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import csv
import os
import datetime

app = FastAPI()

# File to store our 500+ scans
DATA_FILE = "web_scans.csv"

# Ensure CSV exists with headers to include the QR ID
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "QR_ID", "Full_URL"])

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Pro QR Batch Scanner</title>
        <script src="https://unpkg.com/html5-qrcode"></script>
        <style>
            :root {
                --bg-color: #0f1115;
                --surface-color: #1c1f26;
                --primary-color: #10b981;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
                --border-radius: 16px;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; }

            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                display: flex;
                flex-direction: column;
                align-items: center;
                min-height: 100vh;
                padding: 16px;
            }

            .app-container {
                width: 100%;
                max-width: 500px;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            header {
                text-align: center;
                padding: 10px 0;
            }

            h2 {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            }

            .stats-badge {
                display: inline-flex;
                align-items: center;
                background-color: rgba(16, 185, 129, 0.1);
                color: var(--primary-color);
                padding: 8px 18px;
                border-radius: 30px;
                font-weight: 600;
                font-size: 0.95rem;
                border: 1px solid rgba(16, 185, 129, 0.2);
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.05);
            }

            .scanner-card {
                background-color: var(--surface-color);
                border-radius: var(--border-radius);
                padding: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }

            #reader {
                width: 100%;
                border-radius: 8px;
                overflow: hidden;
                border: none !important;
            }

            #reader__scan_region { background-color: #000; }
            #reader video { object-fit: cover; border-radius: 8px; }
            #reader__dashboard_section_csr span { color: var(--text-main) !important; }
            #reader a { color: var(--primary-color) !important; }

            .log-section {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .log-header {
                font-size: 0.95rem;
                font-weight: 600;
                color: var(--text-muted);
                padding-left: 4px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            .log-container {
                display: flex;
                flex-direction: column;
                gap: 10px;
                height: 280px;
                overflow-y: auto;
                padding-right: 4px;
            }

            .log-container::-webkit-scrollbar { width: 4px; }
            .log-container::-webkit-scrollbar-track { background: transparent; }
            .log-container::-webkit-scrollbar-thumb { background: #374151; border-radius: 10px; }

            .log-item {
                background-color: var(--surface-color);
                padding: 14px 16px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                gap: 14px;
                word-break: break-all;
                animation: slideIn 0.25s ease-out;
                border-left: 4px solid var(--primary-color);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }

            .log-icon {
                background-color: rgba(16, 185, 129, 0.15);
                color: var(--primary-color);
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                font-weight: bold;
                font-size: 0.8rem;
            }
            
            .log-content {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            
            .log-id {
                font-size: 1rem;
                font-weight: bold;
                color: var(--primary-color);
            }
            
            .log-url {
                font-size: 0.75rem;
                color: var(--text-muted);
            }

            @keyframes slideIn {
                from { opacity: 0; transform: translateY(-15px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <header>
                <h2>Batch Scanner</h2>
                <div class="stats-badge">
                    <span id="count">0</span>&nbsp;/ 500 Scanned
                </div>
            </header>

            <div class="scanner-card">
                <div id="reader"></div>
            </div>

            <div class="log-section">
                <div class="log-header">Recent Scans</div>
                <div class="log-container" id="log">
                    <!-- Javascript will inject list items here -->
                </div>
            </div>
        </div>

        <script>
            const scannedIds = new Set();
            const logElement = document.getElementById('log');
            const countElement = document.getElementById('count');

            function onScanSuccess(decodedText) {
                let qrId = decodedText; // Default to full text

                try {
                    // Try to parse it as a proper web link
                    const parsedUrl = new URL(decodedText);
                    
                    // Look specifically for "?qr_uid=XXXXX"
                    if (parsedUrl.searchParams.has('qr_uid')) {
                        qrId = parsedUrl.searchParams.get('qr_uid');
                    } 
                    // Fallback just in case you scan an older format (like s.a2deats.com/ID)
                    else {
                        const parts = parsedUrl.pathname.split('/').filter(Boolean);
                        if (parts.length > 0) {
                            qrId = parts[parts.length - 1];
                        }
                    }
                } catch (e) {
                    // If the QR code is just plain text and not a URL, it gracefully falls back
                    console.warn("Not a valid URL, using raw text");
                }

                // Deduplicate based on the extracted ID
                if (!scannedIds.has(qrId)) {
                    scannedIds.add(qrId);
                    
                    // Update the counter
                    countElement.innerText = scannedIds.size;
                    
                    // Create a styled card showing the ID prominently
                    const entry = document.createElement('div');
                    entry.className = 'log-item';
                    entry.innerHTML = `
                        <div class="log-icon">✓</div>
                        <div class="log-content">
                            <span class="log-id">ID: ${qrId}</span>
                            <span class="log-url">${decodedText}</span>
                        </div>
                    `;
                    
                    // Add it to the top of the list
                    logElement.prepend(entry);

                    // Send BOTH the full URL and the extracted ID to the Python Backend
                    fetch('/log-scan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: decodedText, qr_id: qrId })
                    });

                    // Fast haptic pop
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
    qr_id = data.get("qr_id")
    
    # Generate a clean timestamp
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Save to CSV
    with open(DATA_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, qr_id, url])
        
    return {"status": "logged", "recorded_id": qr_id}
