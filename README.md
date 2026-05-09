```markdown
![NetTools Pro Banner](https://via.placeholder.com/1200x300?text=NetTools+Pro+Cloudflare+Edition)  
*Replace with your own banner / screenshot*

![Build](https://github.com/Devtahas/CG_BPB/actions/workflows/build.yml/badge.svg)  
![Release](https://img.shields.io/github/v/release/Devtahas/CG_BPB)  
![License](https://img.shields.io/github/license/Devtahas/CG_BPB)

🌐 **Telegram Channel:** [@DevTaha_project](https://t.me/DevTaha_project)  
🆘 **Support Group:** [@DevTaha_project](https://t.me/DevTaha_project)

---

## 🌟 NetTools Pro — Cloudflare Edition

> **A professional GUI application for network privacy, anti‑censorship, and connection optimisation.**  
> *From Cloudflare IP scanning to VPN chains, WARP, Tor, DNS, and gaming acceleration — all in one place.*

NetTools Pro has evolved from a simple terminal scanner into a full‑featured desktop client, inspired by modern proxy managers like **Hiddify**. It gives you complete control over your internet traffic, whether you want to bypass deep packet inspection, chain several VPN layers, or simply find the fastest Cloudflare endpoint.

---

## 🚀 Key Features

### 🛡️ VPN Client (VLESS / VMess / Trojan / Shadowsocks / Hysteria2 / TUIC / WireGuard)
- Built‑in **Xray‑core** with automatic updates  
- Import configs from subscription links, clipboard, QR code, or JSON files  
- Real‑time ping sorting, quick edit, revive (SNI replacement), and delete  
- **TUN Mode** for system‑wide VPN  
- **Kill Switch** (Windows Firewall) to prevent leaks  

### ⚡ Cloudflare IP Scanner (CF Scanner)
- Multi‑threaded scanning of Cloudflare IP ranges  
- Automatic detection of working ports, handshake verification, and speed testing  
- Generates VLESS configs (WS / gRPC / TCP) with the best DNS  
- **ISP‑aware Fragment** (auto‑tuned for MCI, Irancell, Rightel)  
- One‑click subscription generation and GitHub upload  

### 🌪️ WARP (AmneziaWG Anti‑DPI)
- Integrated AmneziaWG tunnel  
- Built‑in advanced scanner for WARP endpoints  
- Automatic identity generation and connection  

### 🧅 Tor Network & 🅿️ Psiphon
- One‑click Tor connection with country exit node selection  
- Psiphon stealth proxy with background auto‑connect and system proxy  

### 🌍 DNS Changer
- Massive list of DNS servers (IPv4, DoH, DoT, Local CF)  
- **Local Cloudflare DNS Server** (only resolves CF domains for speed)  
- **DNS Hunter** – finds the fastest DNS for a target domain  
- DNS leak test, DNSSEC check, CNAME unmasking, DoH/DoT tester  

### 🆘 Anti‑Filter (Panic Button)
- Multi‑layer survival chain: DNS → Tor → Psiphon → WARP  
- If all layers fail, automatically redirects to the Deep CF Scanner  
- Recovers system proxy and DNS on stop  

### 🎮 Gaming Mode
- System resource monitor (CPU, RAM, GPU)  
- One‑click accelerator: closes background apps, sets process priority  
- Ping stabiliser with FEC (Forward Error Correction)  
- Gaming DNS profiles and NAT optimisation  

### 💬 Secure Messenger (E2E + TLS 1.3)
- Host or join LAN rooms with password protection  
- RSA‑2048 key exchange + AES‑256‑GCM encryption  
- Private messages and system join/leave notifications  

### 🌐 Secure Browser
- Launches Chrome/Edge with custom User‑Agent, proxy, and anti‑fingerprinting flags  
- Tor mode (routes browser through local Tor)  

### 🛠️ Tools & Utilities
- **Pre‑Processor (Traffic Shaping)** – SOCKS5 proxy that mimics real website traffic (Jitter, padding, TLS fingerprint spoofing)  
- **Traffic Mimicry** – Disguise VPN traffic as regular sites (Aparat, YouTube, etc.)  
- **Profile Maker** – Record and replay website behaviour  
- **Datacenter Scanner** – Find clean Iranian IPs that reach Cloudflare Workers  
- **Fastly Scanner** – Scan Fastly CDN edges for usable IPs  
- **Port Scanner** – TCP/SYN/UDP with service detection and OS guessing  
- **UUID & Password Generator**  

### 💾 Smart Storage & Security
- All configs, subscriptions, and settings stored in a user‑selectable folder  
- Optional **AES‑256‑GCM encryption** with master password  
- App lock with password protection  

### 🧩 Plugin System
- Install plugins from ZIP files or a remote worker store  
- Enable/disable plugins; each can add UI panels to existing tabs  

---

## 📸 Screenshots

*Add your own screenshots here. Examples:*

![Main UI](https://via.placeholder.com/800x450?text=VPN+Client+Tab)  
*VPN Client tab with config management*

![Scanner](https://via.placeholder.com/800x450?text=CF+Scanner+Tab)  
*Cloudflare scanner generating configs in real‑time*

---

## 💻 Requirements

- **Windows 10/11** (administrator rights recommended for TUN, DNS, WARP)  
- **Python 3.9+** (if running from source)  
- Internet connection  

*Linux support is partially available but not fully tested.*

---

## 📦 Installation

### Option 1: Download Pre‑built Release (Easiest)
Grab the latest `NetTools.Pro.zip` from the [Releases page](https://github.com/Devtahas/CG_BPB/releases). Extract and run `NetTools Pro.exe`. No Python required.

### Option 2: Run from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/Devtahas/CG_BPB.git
   cd CG_BPB
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.pyw
   ```

> 💡 If the app fails to start due to missing DLLs, install the latest [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe).

---

## ⚙️ First‑Time Setup

1. Launch **NetTools Pro**.  
2. Go to the **⚡ CF Scanner** tab.  
3. Enter your **VLESS UUID** (generate one with the included tool or from [uuidgenerator.net](https://www.uuidgenerator.net)).  
4. Fill in your **Worker Host** and **WS/gRPC Path** (from your Cloudflare Worker / BPB panel).  
5. Adjust scanning settings (ports, networks, fragment) or leave defaults.  
6. Click **▶ START ADVANCED SCAN** – the scanner will find the fastest IPs and generate configs.  
7. Then switch to the **🛡️ VPN Client** tab, select a generated config, and click **▶ CONNECT**.  

> Detailed video tutorials will be added to the Telegram channel soon.

---

## 🧠 Usage Tips

- **Pre‑Processor**: Found in `Tools → Pre‑Processor`. It automatically detects the best whitelist domain and creates a mimicry profile to bypass DPI even before your VPN.  
- **VPN‑in‑VPN Chain**: Use `VPN Client → VPN‑in‑VPN Chain` tab to automatically chain Traffic Mimicry → Pre‑VPN → Main config for maximum resilience.  
- **DNS Changer**: The `Local CF DNS Server` resolves only Cloudflare domains to speed up scanning; it can also be set as your system DNS.  
- **Anti‑Filter Panic Button**: Press it when everything else fails – it will try every bypass method in sequence and finally launch a Deep Scan.

---

## 🔒 Security & Privacy

- All saved configurations can be protected with a **master password** (AES‑256‑GCM).  
- Application lock requires a password to open.  
- Xray‑core and other engines are downloaded from official sources; you can verify checksums if needed.  
- No telemetry or data collection – everything runs locally.

---

## 📜 Disclaimer

This tool is intended for **educational and research purposes** only. The developers are not responsible for any misuse, illegal activities, or damage caused by this software. Ensure that you comply with the laws of your country.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.  
Developers wishing to create plugins should read the `Plugin System` documentation (coming soon).

---

## ⭐ Support the Project

- **Star** the repository ⭐  
- **Report bugs** via GitHub Issues 🐛  
- **Suggest features** in the Telegram group 💬  
- **Share** with friends who need an all‑in‑one network toolbox 📡

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) (see LICENSE file for details).

---

**Made with ❤️ by [@DevTaha](https://github.com/Devtahas) and contributors**
```
