# 🚀 Cloudflare IP Scanner & VLESS Config Generator

A fast, multi-threaded Cloudflare IP Scanner written in Python. This tool scans Cloudflare IP ranges (including hidden BGP routes), tests ping and speed, and automatically generates optimized VLESS (WebSocket + TLS/HTTP2) configurations with Geolocation support.

## 📸 Screenshot
![Scanner Screenshot](لینک_عکسی_که_آپلود_کردی_را_اینجا_بگذار)

## ✨ Features
- **Mega BGP Scanning:** Scans official and hidden Cloudflare IP ranges.
- **HTTP/2 Support:** Generates ALPN `h2` configs to bypass SNI blocking effectively.
- **Geolocation:** Automatically detects the country of clean IPs (e.g., 🌍US, 🌍DE).
- **Auto-Sub Generation:** Exports a `sub.txt` file containing base64 encoded VLESS links.
- **Smart Speed Test:** Tests both download and upload speeds.

## 📥 Download
You don't need to install Python! Just download the pre-compiled `.exe` file for Windows from the [Releases](../../releases) page.

## 💻 How to Run (Source Code)
If you prefer running the Python script directly:
```bash
pip install -r requirements.txt
python bpb2.py
