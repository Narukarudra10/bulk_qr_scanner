import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import cv2
from pyzbar.pyzbar import decode
import csv
import os
from urllib.parse import urlparse, parse_qs
import datetime
import threading

# --- Config & Setup ---
st.set_page_config(page_title="Batch QR Scanner", layout="centered", initial_sidebar_state="collapsed")
DATA_FILE = "scans.csv"

# Thread-safe memory to prevent duplicates during the video stream
scanned_ids = set()
lock = threading.Lock()

# Initialize CSV if it doesn't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "QR_ID", "Full_URL"])
else:
    # Load existing scans into memory so we don't duplicate on page reload
    with open(DATA_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scanned_ids.add(row["QR_ID"])

# --- URL Extraction Logic ---
def extract_qr_id(url):
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if 'qr_uid' in query:
            return query['qr_uid'][0]
        else:
            parts = [p for p in parsed.path.split('/') if p]
            if parts:
                return parts[-1]
    except Exception:
        pass
    return url  # Fallback to raw text

# --- Real-Time Video Processor ---
class QRVideoProcessor(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded_objs = decode(img)

        for obj in decoded_objs:
            qr_text = obj.data.decode('utf-8')
            qr_id = extract_qr_id(qr_text)

            # Check for duplicates safely across threads
            with lock:
                if qr_id not in scanned_ids:
                    scanned_ids.add(qr_id)
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Log silently to CSV
                    with open(DATA_FILE, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp, qr_id, qr_text])

            # Draw visual feedback on the camera feed
            pts = obj.polygon
            if len(pts) == 4:
                import numpy as np
                pts = np.array([tuple(p) for p in pts], dtype=np.int32)
                cv2.polylines(img, [pts], True, (0, 255, 0), 4)
            
            # Display the scanned ID
            cv2.putText(img, f"ID: {qr_id}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Always draw the total count on the screen so you know it's working
        with lock:
            current_count = len(scanned_ids)
        cv2.putText(img, f"Total Scanned: {current_count} / 500", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 0), 2)

        return img

# --- UI Layout ---
st.title("📲 High-Speed Batch Scanner")
st.markdown("Stream your camera to process QR codes in bulk. **Slide your 500 pieces under the camera.**")

# The WebRTC Video Player
webrtc_streamer(
    key="qr-scanner",
    mode=WebRtcMode.SENDRECV,
    video_transformer_factory=QRVideoProcessor,
    media_stream_constraints={"video": {"facingMode": "environment"}, "audio": False},
    async_transform=True,
)

st.divider()

# Dashboard to view results
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("Database Log")
with col2:
    if st.button("🔄 Refresh Data"):
        st.rerun()

# Read and display the CSV
if os.path.exists(DATA_FILE):
    import pandas as pd
    df = pd.read_csv(DATA_FILE)
    st.dataframe(df, use_container_width=True, hide_index=True)
