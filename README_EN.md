# NetTools Pro – Cloudflare Edition
**English** | **[فارسی](README.md)**


... (بقیه محتوای انگلیسی)
**NetTools Pro** is an all‑in‑one Windows application for network engineers, privacy enthusiasts, and anyone who needs to bypass internet censorship or optimize their connection.  
It combines a modern VPN client, advanced scanners, DPI‑bypass techniques, DNS management, and many other tools in a single, user‑friendly interface.

> **Version 9.8** – Major update from the old terminal‑based version. Now a full desktop application built with CustomTkinter.

---

## 🚀 Key Features

- **VPN Client** – Import and manage VLESS, VMess, Shadowsocks, Trojan, Hysteria2, TUIC, WireGuard, SOCKS and HTTP proxies. Supports TUN mode, Kill Switch, Pre‑VPN chaining, Traffic Mimicry, and automated Xray‑core updates.
- **CF Scanner** – Find the fastest Cloudflare IPs for your worker configuration. Multi‑threaded, with custom CIDR, DNS, and port management. Automatic fragment tuning based on your ISP.
- **Telegram Proxy** – Fetch MTProto proxies from Telegram channels, ping them in real time, and copy the connection link with one click.
- **Tools & Generators** – A rich set of utilities:
  - UUID / Password generator
  - Config extractor (parse VLESS JSON)
  - Professional port scanner (TCP connect, SYN stealth, UDP) with device/OS detection
  - Profile Maker (record and replay website traffic)
  - Datacenter Scanner (find clean Iranian IPs for Pre‑VPN chains)
  - DNS Scanner (test latency and health of DNS servers)
  - Fastly Scanner (discover Fastly edge IPs)
  - **Local Traffic Pre‑Processor** – Shape your traffic to mimic a normal website before it leaves your device.
- **Speed Test** – Measure ping, download, and upload speed using Cloudflare’s infrastructure.
- **Storage & Assets** – Manage your IP ranges and DNS lists centrally. Browse and edit all generated configuration files.
- **DNS Changer** – Switch system DNS with one click. Supports IPv4, DoH, DoT, and a local Cloudflare DNS server.
- **WARP (AmneziaWG)** – Connect through Cloudflare WARP using the AmneziaWG driver. Includes an advanced endpoint scanner.
- **Psiphon** – Launch Psiphon 3 in stealth mode (no visible window).
- **Tor Network** – Run the Tor expert bundle directly from the app and route all system traffic.
- **Anti‑Filter (Panic Mode)** – Multi‑layer survival chain: DNS hunt → Tor → Psiphon → WireGuard → auto‑redirect to Scanner.
- **Gaming Mode** – System accelerator (kill background apps), ping stabilizer (FEC), NAT optimizer, and gaming DNS.
- **Secure Messenger** – Self‑hosted, end‑to‑end encrypted chat with TLS 1.3 and LAN discovery.
- **Secure Browser** – Launch Chrome/Edge with custom User‑Agent, proxy support, Tor mode, and anti‑fingerprinting flags.
- **Dashboard** – Real‑time network quality index, live speed graphs, service status, and packet path visualization.
- **Settings** – Update cores (Xray, GoodbyeDPI), enable AES‑256‑GCM storage encryption, set app lock, and change storage location.
- **Plugin System** – Extend the app by installing plugins from ZIP or from the online marketplace.

---

## 📥 Installation

### Option 1 – Pre‑built EXE (Recommended)
1. Go to the [Releases page](https://github.com/Devtahas/CG_BPB/releases) and download the latest `NetTools_Pro_Release.zip`.
2. Extract the archive to any folder.
3. (Optional) Place the required core files (`xray.exe`, `tor.exe`, `amneziawg.exe`, `psiphon3.exe`) inside the `cores` subfolder if they are not already bundled.
4. Run `NetTools_Pro.exe` **as Administrator** (right‑click → Run as administrator).  
   *Administrator rights are required for changing system DNS, installing TUN interfaces, and running Kill Switch.*

### Option 2 – Run from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/Devtahas/CG_BPB.git
   cd CG_BPB
   ```
2. Install Python 3.11+
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Place the core binaries (`xray.exe`, `tor.exe`, `amneziawg.exe`, `psiphon3.exe`) inside `cores/` (or download them later via the app’s Settings).
5. Launch the application:
   ```bash
   python main.pyw
   ```

---

## 📖 Usage Guide

### 🛡️ VPN Client
The heart of the application.  
- **Import Configs:** Paste a VLESS/VMess/etc. link, a subscription URL, or scan a QR code.
- **Manage Configs:** View, edit, delete, or “revive” configs (force a new SNI using a mimicry profile).
- **Connection:** Select a config, choose TUN mode (global VPN) if needed, and click **CONNECT**.  
  - **Pre‑VPN Chain:** Use a datacenter‑scanned IP as a middle proxy.  
  - **Traffic Mimicry:** Disguise your VPN traffic as a regular website (Aparat, YouTube, etc.) by selecting a profile.
- **Advanced DPI Bypass:** Enable Fragment, SNI Spoofing, REALITY, FakeTLS, and more before connecting.

### ⚡ CF Scanner
Find the best Cloudflare IPs for your VLESS worker.  
- Fill in your UUID, Worker Host, and WS/gRPC Path.  
- Start the scan. The scanner tests thousands of IPs, measures latency and speed, and generates ready‑to‑use configs and a subscription link.  
- Manage CIDR ranges, custom ports, and DNS servers through the built‑in managers.

### ✈️ Telegram Proxy
Fetch MTProto proxies from a Telegram channel (default: `ProxyMTProto`).  
- Click **Fetch & Ping** – the app scrapes the channel, pings each proxy, and shows the fastest ones.  
- Copy the `tg://` link directly to your clipboard.

### 🛠️ Tools & Generators
- **Generators:** Create random UUIDs and secure passwords.  
- **Config Extractor:** Paste a VLESS JSON and instantly extract UUID, Host, and Path.  
- **Port Scanner:** Professional scanner with three modes: TCP Connect, SYN Stealth (requires Scapy), and UDP. Detects open ports, guesses service and operating system, and identifies devices (cameras, routers, etc.).
- **Profile Maker:** Record the traffic of a website and replay it later to generate background noise.
- **Datacenter Scanner:** Scans Iranian datacenter IPs to find clean addresses that can reach your Cloudflare Worker. Generates Pre‑VPN configs for chaining.
- **DNS Scanner:** Test latency and reliability of multiple DNS servers simultaneously.
- **Fastly Scanner:** Similar to Datacenter Scanner but targets Fastly edge IPs.
- **Pre‑Processor:** A local SOCKS5 proxy that alters your traffic pattern (TLS fingerprint, padding, jitter) to make it look like a whitelisted website. Perfect for bypassing deep packet inspection.

### 🚀 Speed Test
Real‑time measurement of your Ping, Download, and Upload speed using Cloudflare’s global network.

### 💾 Storage & Assets
- **Storage Path:** You can move all configuration data (configs, subscriptions, settings) to a custom location.  
- **IP & DNS Assets:** Centrally manage the IP ranges (Cloudflare, Datacenter, Fastly) and DNS servers used by all scanners.

### 🌍 DNS Changer
- Choose from a large built‑in list of DNS providers (Google, Cloudflare, Quad9, Shecan, Electro…).  
- Add custom IPv4, DoH, or DoT servers.  
- Activate a **Local Cloudflare DNS Server** that resolves Cloudflare domains using the best IPs from your scanned list.  
- DNS Leak test, DNSSEC checker, CNAME unmasker, and Split DNS configuration.

### 🌪️ WARP (AmneziaWG)
- Generate a WARP identity and connect using the AmneziaWG driver (anti‑DPI WireGuard fork).  
- Use the **Advanced Scanner** to find the fastest WARP endpoint.

### 🅿️ Psiphon
Launch the Psiphon 3 client in the background. The application automatically hides its window and monitors the connection.

### 🧅 Tor
Start the Tor expert bundle, monitor bootstrap progress, and route your entire system through the Tor network.

### 🆘 Anti‑Filter (Panic Mode)
When everything fails, this survival mechanism chains multiple protocols:
1. Finds the fastest DNS
2. Attempts to connect via Tor
3. Falls back to Psiphon
4. Tries WireGuard (AmneziaWG)
5. If all else fails, it automatically opens the **CF Scanner** to hunt for new working endpoints.

### 🎮 Gaming Mode
- **System Accelerator:** Closes background apps and sets game processes to high priority.  
- **Ping Stabilizer:** Reduces packet loss using a Forward Error Correction (FEC) algorithm.  
- **NAT Optimizer:** Adjusts Windows TCP settings for lower latency.  
- **Gaming DNS:** Apply DNS servers optimized for gaming (lower ping).

### 💬 Secure Messenger
- **Host a Room:** Start an encrypted chat server on your local network. Optionally set a room password.  
- **Join a Room:** Connect to a hosted room by entering the IP, port, and username.  
- All messages are **end‑to‑end encrypted** (RSA‑2048 key exchange + AES‑256‑GCM) and transmitted over TLS 1.3.

### 🌐 Secure Browser
Launch Chrome or Edge with enhanced privacy settings:
- Custom User‑Agent (impersonate Chrome, Firefox, Safari, etc.)
- Anti‑fingerprinting flags (disable WebRTC, Canvas, etc.)
- Built‑in proxy and Tor mode (routes through 127.0.0.1:9050)
- Ad blocking via system hosts file

### 📊 Dashboard
A live monitoring panel that shows:
- **Network Quality Index** (based on ping and packet loss)
- Real‑time upload/download speed graph
- Active services status (VPN, DNS, Tor, etc.)
- Public IP and ISP information
- Animated packet path visualization

### ⚙️ Settings
- **Core Updates:** Check for and install the latest Xray‑core and GoodbyeDPI automatically.
- **Security:** Enable **AES‑256‑GCM storage encryption** to protect all your configs and settings with a master password. You can also set an **application lock** password.
- **Storage:** Change the default data directory (by default, it’s next to the application executable for portability).
- **Appearance:** Switch between Dark and Light themes; change language (English / Persian).

### 🧩 Plugins
Extend the functionality of NetTools Pro by installing third‑party plugins.  
You can import a plugin from a **ZIP file** or download it directly from the online **Plugin Store** (requires a Cloudflare Worker backend).  
Plugins can add new tabs to existing sections (Scanner, VPN, Tools, etc.) or run in the background.

---

## ⚙️ Configuration & Storage

By default, all user data is stored in a `NetTools_Data` folder next to the executable.  
You can change this location from **Settings → Storage**.

Important files and folders:
- `Configs/` – All generated and imported VPN configuration files (JSON).
- `Subscriptions/` – Subscription links (Base64‑encoded).
- `Settings/` – Application settings, DNS lists, IP ranges, mimicry profiles, and the encrypted database.
- `cores/` – Place Xray‑core (`xray.exe`), Tor (`tor.exe`), AmneziaWG (`amneziawg.exe`), and Psiphon (`psiphon3.exe`) here.

---

## 🔧 Building from Source

If you want to package the application yourself:

1. **Install dependencies** (see requirements.txt).
2. **Ensure** the following folders exist in the project root:
   - `cores/` (with `xray.exe`, `tor.exe`, `amneziawg.exe`, `psiphon3.exe`)
   - (Optional) `xray/` (if you want to bundle Xray separately)
3. Run PyInstaller:
   ```bash
   pyinstaller --onefile --noconsole --uac-admin --icon=icon.ico `
       --add-data "cores;cores" `
       --collect-all customtkinter `
       --collect-all pyzbar `
       ...
       --name NetTools_Pro main.pyw
   ```
4. The output executable will be inside the `dist/` folder.

---

## 🤝 Credits

- **Developer:** Devtahas  
- **GitHub:** [https://github.com/Devtahas/CG_BPB](https://github.com/Devtahas/CG_BPB)  
- **Libraries:** Xray‑core, CustomTkinter, Psutil, Cryptography, dnspython, Scapy, and many more.  
- **Special thanks** to all the developers of the open‑source tools that made this project possible.

---

## 📜 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

> **Disclaimer:** This software is intended for educational and privacy protection purposes only. The developer is not responsible for any misuse or violation of local laws.
