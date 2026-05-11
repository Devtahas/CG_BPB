# NetTools Pro – Cloudflare Edition

**NetTools Pro** is a comprehensive Windows application designed for network engineers, security researchers, and anyone seeking to optimize their internet connection, bypass censorship, or enhance their privacy. It integrates a powerful VPN client, multiple scanners, DPI‑bypass tools, DNS management, and a suite of network utilities into a single, modern graphical interface.

> **Version 9.8** – A massive upgrade from the old terminal‑based version. Now a full desktop application built with CustomTkinter.

---

## 🚀 Feature Overview

- **VPN Client** – Import, manage, and connect to VLESS, VMess, Shadowsocks, Trojan, Hysteria2, TUIC, WireGuard, SOCKS, and HTTP proxies. Supports TUN mode, Kill Switch, Pre‑VPN chaining, Traffic Mimicry, and automatic Xray‑core updates.
- **CF Scanner** – Multi‑threaded scanner to find the fastest Cloudflare IPs for your worker configuration. Custom CIDR ranges, DNS servers, port lists, and automatic fragment tuning based on ISP.
- **Telegram Proxy** – Fetch MTProto proxies from Telegram channels, test latency in real time, and copy the connection link with one click.
- **Tools & Generators** – A rich toolbox including:
  - UUID / Password generator
  - Config extractor
  - Port scanner (TCP, SYN Stealth, UDP) with OS and device detection
  - Profile Maker (website traffic recording and replay)
  - Datacenter Scanner (find clean Iranian IPs for Pre‑VPN chains)
  - DNS Scanner
  - Fastly Scanner
  - **Local Traffic Pre‑Processor** – Shape your traffic to mimic a whitelisted website before it leaves your device.
- **Speed Test** – Measure ping, download, and upload using Cloudflare's infrastructure.
- **Storage & Assets** – Manage IP ranges and DNS lists centrally; browse and edit generated configuration files.
- **DNS Changer** – Change system DNS with a single click. Supports IPv4, DoH, DoT, and a local Cloudflare DNS server.
- **WARP (AmneziaWG)** – Connect via Cloudflare WARP using the anti‑DPI AmneziaWG driver. Advanced endpoint scanner included.
- **Psiphon** – Launch Psiphon 3 in stealth mode (no visible window).
- **Tor Network** – Run the Tor expert bundle directly from within the app.
- **Anti‑Filter (Panic Mode)** – Multi‑layer survival chain: DNS hunt → Tor → Psiphon → WireGuard → auto‑redirect to Scanner.
- **Gaming Mode** – System accelerator, ping stabilizer (FEC), NAT optimizer, and gaming DNS.
- **Secure Messenger** – Self‑hosted, end‑to‑end encrypted chat with TLS 1.3 and LAN discovery.
- **Secure Browser** – Launch Chrome/Edge with custom User‑Agent, proxy, Tor mode, and anti‑fingerprinting flags.
- **Dashboard** – Real‑time network quality index, live speed graph, service status, and packet path visualization.
- **Settings** – Update cores (Xray, GoodbyeDPI), enable AES‑256‑GCM storage encryption, set an app lock, change storage path.
- **Plugin System** – Extend the app by installing plugins from ZIP files or the online Plugin Store.

---

## 📥 Installation

### Option 1 – Pre‑built Executable (Recommended)
1. Go to the [Releases page](https://github.com/Devtahas/CG_BPB/releases) and download the latest `NetTools_Pro_Release.zip`.
2. Extract the archive to any folder.
3. (Optional) If the core binaries are not already bundled, place them inside the `cores` folder:
   - `xray.exe` (Xray‑core)
   - `tor.exe` (Tor expert bundle)
   - `amneziawg.exe` (AmneziaWG driver)
   - `psiphon3.exe` (Psiphon client)
4. Run `NetTools_Pro.exe` **as Administrator** (right‑click → Run as administrator). Administrator privileges are required for changing system DNS, installing TUN interfaces, and using Kill Switch.

### Option 2 – Run from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/Devtahas/CG_BPB.git
   cd CG_BPB
   ```
2. Install Python 3.11+.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Place the required core binaries (`xray.exe`, `tor.exe`, `amneziawg.exe`, `psiphon3.exe`) inside the `cores` folder (or download them later via the app’s Settings).
5. Launch:
   ```bash
   python main.pyw
   ```

---

## 📖 In‑Depth Usage Guide

### 🛡️ VPN Client
The VPN client is the heart of the application. It handles all aspects of creating, importing, managing, and connecting to proxy/VPN configurations.

**Main Connection Tab:**
- **Importing Configs:** Click **Paste** to import a single VLESS/VMess/etc. link from the clipboard, **Sub Link** to fetch and decode a subscription URL (Base64‑encoded list of links), or **QR** to scan a QR code directly from your screen.
- **Config List:** All imported configurations appear in the scrollable list. Each entry shows the protocol type, a ping indicator (which you can refresh by clicking **Pings**), and action buttons (Edit, Delete, Revive).
- **Selecting a Config:** Click on a config to select it. The selected config will be highlighted.
- **TUN Mode:** Enable **TUN Mode** before connecting to route all system traffic through the VPN (requires Administrator privileges and a TUN‑capable config).
- **Connection:** Click **CONNECT**. The app automatically patches the selected config with the required inbound settings (SOCKS on port 10808, HTTP on 10809, optional TUN), applies DPI‑bypass techniques, starts any enabled chains (Pre‑VPN, Mimicry), and launches Xray‑core. The status indicator will change to “Connected”.
- **Traffic Monitor:** Real‑time download/upload speed is displayed.
- **IP Check:** Click **Check My IP** to see your current public IP and ISP.

**Pre‑VPN Chain Tab:**
- Enables routing your traffic through a *clean Iranian datacenter IP* before reaching the final server. This is useful when your ISP blocks direct connections to Cloudflare Workers.
- First, use the **Datacenter Scanner** (in Tools) to generate `[PreVPN]` configs. They will appear in this tab’s dropdown.
- Select a Pre‑VPN config and enable **Pre‑VPN Chaining**. The main connection will then route through that IP.

**Advanced DPI Bypass Tab:**
- **TLS 1.3:** Force TLS 1.3 only.
- **SNI Spoofing:** Replace the real Server Name Indication with a fake one (e.g., `www.google.com`) to evade SNI‑based filtering.
- **REALITY Protocol:** Use the most advanced anti‑DPI protocol. Requires a REALITY‑enabled server and its public key.
- **Packet Fragmentation:** Split the first packet into small fragments to confuse DPI systems.
- **FakeTLS / FakeHTTP:** Disguise traffic as normal HTTPS/HTTP (requires GoodbyeDPI).
- All settings are applied when you click **Apply Selected Methods**. You must reconnect for changes to take effect.

**Traffic Mimicry Tab:**
- This feature makes your encrypted VPN traffic look like a normal visit to a whitelisted website (e.g., Aparat, YouTube).
- **Auto‑Generate Profile:** Enter a URL and click **Generate Profile** to automatically analyze the site and create a mimicry profile.
- **Record Full (10m):** Record 10 minutes of real browser traffic on the target site to build a highly accurate profile (requires Selenium + Scapy).
- Select a profile from the list, enable **Enable Traffic Mimicry**, and connect as usual.
- All your traffic will inherit the TLS fingerprint, HTTP headers, packet timing, and padding patterns of the selected site.

**VPN‑in‑VPN Chain Tab:**
- An intelligent assistant that automatically selects the best DNS, port, config, fragment, and fingerprint based on your current network conditions, then launches a multi‑layer chain (Mimicry → Pre‑VPN → Main). Essentially a one‑click optimization and connect.

**Config Explorer Tab:**
- Browse, edit, rename, delete, import/export individual JSON config files with a built‑in JSON viewer and quick‑edit fields (UUID, Host, Path).

---

### ⚡ CF Scanner
The Cloudflare Scanner finds optimal IP addresses for your Cloudflare Worker.

- **Mandatory Fields:** Enter your VLESS UUID, Worker Host (e.g., `app.workers.dev`), and WS/gRPC Path (`/ws`).
- **IP Source:** Choose between the built‑in Cloudflare CIDR list or fetching the latest IPs from an online API.
- **Port Mode:** Standard (common ports like 443, 2053, etc.) or Deep Scan (all 1‑65535 ports).
- **Config Types:** Select which security types (TLS/None) and ALPNs (H2/HTTP1.1) to generate.
- **Network Types:** Enable WebSocket, gRPC, and/or TCP configs.
- **Fragment:** Enable Auto (detects ISP and picks optimal fragment settings) or Manual.
- **Threads & IPs per Range:** Adjust to balance speed and system load.
- **Start Scan:** The scanner tests thousands of IPs, measures latency and download speed, and builds the best results.
- After the scan, configs are automatically saved to the `Configs` folder, and a subscription link is generated.
- **CIDR Manager:** Customize the Cloudflare IP ranges used by the scanner. You can paste, add, remove, or reset to defaults.
- **DNS Manager:** Edit the list of DNS servers used for testing.
- **Ports Manager:** Modify the list of ports to scan and the network protocols.

---

### ✈️ Telegram Proxy
- Enter the Telegram channel username (default: `ProxyMTProto`).
- Click **Fetch & Ping**. The app scrapes the channel for MTProto proxy links, pings each one simultaneously, and displays the fastest proxies with their latency.
- Click **Copy** on any proxy to get the `tg://` link and share it directly in Telegram.

---

### 🛠️ Tools & Generators
This tab contains multiple specialized utilities, organized in sub‑tabs.

**Generators:**
- **UUID Generator:** Creates a random UUID version 4, ideal for VLESS configurations.
- **Password Generator:** Generates a cryptographically secure random password (16 characters).

**Config Extractor:**
- Paste a VLESS JSON configuration into the textbox and click **EXTRACT DATA**. It will automatically fill the UUID, Host, and Path fields, which you can then copy individually.

**Port Scanner:**
- **Target:** Enter a single IP, domain, or an IP range (e.g., `192.168.1.1-192.168.1.20`).
- **Port Range:** Choose from presets (Common, Web, All) or enter a custom range (e.g., `1-1000,3306,8080`).
- **Scan Mode:** TCP Connect (standard), SYN Stealth (requires Scapy & Npcap), UDP Scan.
- **Live Host Discovery:** First checks which hosts are alive (ping) before scanning ports.
- **Service Detection:** Grabs banners from open ports to identify the service (HTTP, SSH, RDP, etc.).
- **OS Detection (Basic):** Estimates the remote operating system using the TTL value.
- **Device Hints:** Recognizes common devices like cameras (port 554), printers (9100), IoT (port 502), etc.
- Results are displayed in real time and can be exported to JSON or CSV.

**Profile Maker:**
- **Record:** Enter a URL and a profile name, set a browser fingerprint (Chrome, Firefox, etc.) and duration. The app will visit the site, capture all HTTP requests and delays, and save the sequence as a JSON profile.
- **Replay:** Select a saved profile, set a loop count (0 = infinite), optionally add random jitter, and start the simulation. This generates background traffic that mimics the recorded website, useful for anti‑DPI purposes.

**Datacenter Scanner:**
- Scans Iranian datacenter IP ranges (e.g., from MCI, Irancell, etc.) to find addresses that can successfully connect to your Cloudflare Worker.
- Enter the Worker Host, Path, and your VLESS UUID. Select ports to test. The scanner performs a full TLS+WebSocket handshake with the correct SNI, and if successful, generates a Pre‑VPN config that can be used in the VPN Client’s Pre‑VPN Chain.
- Also works with the **Pre‑Processor** proxy if it’s running.

**DNS Scanner:**
- Input a list of DNS servers (one per line) and a test domain.
- The scanner measures latency using real DNS queries (A record) and checks DNSSEC validation.
- Results are sorted by speed and can be exported.

**Fastly Scanner:**
- Similar to the Datacenter Scanner but targets Fastly edge IP ranges. Useful if your worker is behind Fastly CDN.

**Pre‑Processor (Local Traffic Shaper):**
- Found within the Tools tab (the sub‑tab labeled **🛡️ Pre‑Processor**).
- Select a whitelist profile (or auto‑detect the best site), click **Load Selected**, then start the proxy.
- A SOCKS5 proxy runs on `127.0.0.1:10815`. Any application (including the built‑in scanners) can be pointed to this proxy. The Pre‑Processor will alter the TLS fingerprint, add random padding, insert jitter, and simulate burst patterns so that the traffic appears to come from a normal website.
- **Auto‑Detect Best Site:** Automatically tests a list of popular websites (Aparat, Digikala, Google, etc.) to find the fastest reachable one, then creates a mimicry profile for it.

---

### 🚀 Speed Test
- A simple, real‑time test that measures:
  - **Ping:** Average latency to Cloudflare.
  - **Download Speed:** Downloads a 25 MB file in chunks, showing live progress.
  - **Upload Speed:** Uploads small files repeatedly and calculates the average.

---

### 💾 Storage & Assets
- **Storage Path Tab:** View and change the directory where all data (configs, subscriptions, settings) is stored. The default location is next to the application executable for portability.
- **IP & DNS Assets Tab:** Centrally manage the IP range lists (Cloudflare, Datacenter, Fastly) and DNS servers that all other sections of the app rely on. Changes here automatically propagate to the CF Scanner, Datacenter Scanner, DNS Changer, and many other tools.

---

### 🌍 DNS Changer
- **Main Tab:** Select a DNS server from the extensive pre‑configured list (Google, Cloudflare, Quad9, Shecan, Electro, Radar, etc.), view its latency, and connect with one click. The system DNS is set via `netsh`.
- **Tools Tab:** DNS Leak Test, DNSSEC Checker, CNAME Unmasker, and DoH/DoT Tester.
- **DNS Hunter Tab:** Automatically scan a list of DNS servers against a target domain (e.g., Telegram) to find the fastest, cleanest DNS that can actually resolve the domain. Results can be synced to the CF Scanner.
- **Advanced Tab:**
  - **Split DNS:** Route specific domains to different DNS servers.
  - **FakeDNS:** Run a local server that returns fake IPs for specific domains (useful for blocking or testing).
  - **Smart DNS:** Automatically pick the best DNS based on the type of website (streaming, social, gaming).
  - **DNS Cache:** Clear the local DNS cache.
  - **DNSCrypt:** Guidance for using DNSCrypt‑proxy.

---

### 🌪️ WARP (AmneziaWG)
- **Generate New Identity:** Creates a new WireGuard key pair, registers with Cloudflare, and obtains a free WARP account.
- **Endpoint Selection:** Choose the best WARP endpoint (IP:port). The built‑in **Advanced Scanner** can test hundreds of endpoints to find the one with the lowest latency.
- **Connection:** Click **CONNECT** to install the AmneziaWG tunnel service and route your traffic through WARP. Disconnecting will cleanly remove the service.

---

### 🅿️ Psiphon
- Click **LAUNCH PSIPHON**. The app launches `psiphon3.exe` in the background, immediately hides its window, and displays a progress bar. As soon as the system proxy is set by Psiphon, the status updates to “Connected”.
- Disconnect stops the process and resets the proxy.

---

### 🧅 Tor
- Optionally select an exit node country.
- Click **CONNECT TOR**. The app starts the Tor expert bundle, monitors the bootstrap progress (0‑100%), and once complete, sets the system proxy to `127.0.0.1:9052` (HTTP tunnel). All Windows traffic is then routed through Tor.
- Disconnect stops Tor and resets the proxy.

---

### 🆘 Anti‑Filter (Panic Mode)
When standard censorship bypass methods fail, this survival engine tries multiple strategies sequentially:
1. Scans a massive list of DNS servers to find the fastest one, then sets it as the system DNS.
2. Attempts to connect via Tor. If Tor succeeds, it stops.
3. If Tor fails, it tries Psiphon.
4. If Psiphon fails, it tries WireGuard (WARP).
5. If all fail, it automatically switches to the **CF Scanner** tab to hunt for new working endpoints.

The user can monitor each phase in real time.

---

### 🎮 Gaming Mode
- **Performance Tab:**
  - **System Resources:** Live CPU, RAM, and GPU usage bars.
  - **Game Accelerator:** Terminates high‑usage background processes (Chrome, Discord, etc.) and sets game processes to high priority.
  - **Process List:** Shows the top resource‑consuming processes; you can select and kill them.
- **Network Tab:**
  - **Ping Stabilizer:** Employs a Forward Error Correction (FEC) algorithm to compensate for packet loss. You can set a target IP.
  - **NAT Optimization:** Tweaks Windows TCP settings (AutoTuning, Window Size) for lower latency.
  - **Network Statistics:** Shows current ping and packet loss.
- **DNS Tab:** Select from a list of gaming‑optimized DNS servers.

---

### 💬 Secure Messenger
- **Chat Tab:** The main chat interface. Shows messages in real time when connected to a room.
- **Host Room Tab:** Start a server on a chosen port (default 8888). Optionally set a room password. Your local IP is displayed for others to connect.
- **Join Room Tab:** Enter the server IP, port, username, and password (if any) to join.
- All messages are encrypted end‑to‑end (RSA‑2048 key exchange + AES‑256‑GCM). The connection uses TLS 1.3.
- Private messages can be sent using the `/pv <username> <message>` command.

---

### 🌐 Secure Browser
- **Privacy Tab:**
  - **User‑Agent Changer:** Impersonate different browsers/platforms.
  - **Anti‑Fingerprinting Flags:** Adds command‑line flags to disable WebRTC, Canvas, WebGL, etc.
  - **Ad Blocking:** Modifies the system hosts file to block known ad servers (requires Administrator).
- **Network Tab:**
  - **Proxy Settings:** Configure a SOCKS5 or HTTP proxy.
  - **Tor Mode:** Automatically routes the browser through the Tor network (requires Tor to be running).
- **Other Tab:** Add any custom Chrome/Edge command‑line flags.
- Click **Open Browser** to launch with all selected settings.

---

### 📊 Dashboard
- **Overview Tab:** Network Quality Index (0‑100) calculated from ping and packet loss. Summary of active services. Public IP and ISP details.
- **Network Tab:** Real‑time ping, packet loss, and speed (download/upload). A live matplotlib graph of throughput.
- **Services Tab:** Visual status of all major services (VPN, DNS, WARP, Tor, Psiphon, Anti‑Filter, Gaming, Messenger).
- **Packet Path Tab:** An animated diagram showing your data’s journey. DPI/anti‑filter action summary and smart route suggestions.

---

### ⚙️ Settings
- **Updates Tab:** Check for and update Xray‑core and GoodbyeDPI. Displays current and latest versions, download progress.
- **Security Tab:**
  - **Storage Encryption:** Enable AES‑256‑GCM encryption for all your config and settings files. Set a master password; without it, the data cannot be decrypted.
  - **Application Lock:** Set a password that must be entered every time the app starts.
- **Storage Tab:** Change the root data directory. The default is next to the executable (portable). A restart is recommended after changing.
- **Appearance Tab:** Switch between Dark and Light theme; change language.
- **About Tab:** Version information, GitHub link, issue reporter.

---

### 🧩 Plugins
- The **Plugins** tab shows all installed plugins, their status (active/inactive), and provides options to enable/disable or delete them.
- **Install from ZIP:** Import a `.zip` plugin package containing a `manifest.json` and Python code.
- **Install from Store:** Enter a plugin ID to download and install directly from a Cloudflare Worker store (the Worker URL can be configured by the user).
- Plugin developers can create custom tabs that appear in various sections (Scanner, VPN, DNS, etc.) by adhering to the `BasePlugin` interface.

---

## ⚙️ Configuration & Storage Details

By default, user data is kept in a `NetTools_Data` folder next to the executable. The internal structure is:
```
NetTools_Data/
├── Configs/         # VPN config files (.json, possibly encrypted)
├── Subscriptions/   # Generated subscription links
└── Settings/        # App settings, IP lists, DNS lists, profiles, keys
    ├── ip_lists.json
    ├── dns_list.json
    ├── crypto_config.json
    └── mimicry_profiles/
```
The application uses the `cryptography` library to optionally encrypt all sensitive files. Encryption is disabled by default and can be turned on via **Settings → Security**.

---

## 🔧 Building from Source

If you want to compile the app yourself:
1. Install Python 3.11+ and required packages from `requirements.txt`.
2. Ensure the `cores` folder contains `xray.exe`, `tor.exe`, `amneziawg.exe`, `psiphon3.exe`.
3. Run PyInstaller (a sample command is provided in the repository’s workflow file).
4. The output will be a single `NetTools_Pro.exe` in the `dist` folder.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue to discuss any major changes before submitting a Pull Request.  
When contributing:
- Ensure your code matches the existing style.
- Test your changes thoroughly.
- Update any relevant documentation (both `README.md` and `README_EN.md`).

---

## 📜 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

## 🙏 Credits

- **Developer:** Devtahas
- **GitHub:** [https://github.com/Devtahas/CG_BPB](https://github.com/Devtahas/CG_BPB)
- Built with: CustomTkinter, Xray‑core, Psutil, Cryptography, dnspython, Scapy, and many other open‑source projects.

---

> **Disclaimer:** This software is provided for educational and privacy‑protection purposes. The developer is not responsible for any misuse or violation of local laws.
