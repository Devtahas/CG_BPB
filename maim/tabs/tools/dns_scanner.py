# tabs/tools/dns_scanner.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import socket
import dns.resolver
import dns.query
import dns.message
import time
from concurrent.futures import ThreadPoolExecutor
from config import CF_ORANGE, BG_PANEL


class DNSScanner(ctk.CTkFrame):
    """تب اسکنر DNS - تست سرعت و سلامت سرورهای DNS"""
    
    def __init__(self, parent, tabview):
        self.parent = parent
        self.tab = tabview.add("🔍 DNS Scanner")
        self.setup_ui()
        self.results = []
        
    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self.tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        header_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(header_frame, text="🌐 DNS Speed & Health Scanner", font=ctk.CTkFont(size=18, weight="bold"), text_color=CF_ORANGE).pack(pady=(15,5))
        ctk.CTkLabel(header_frame, text="Test latency, reliability, and security of DNS servers", text_color="gray").pack()
        
        # DNS list input
        list_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        list_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(list_frame, text="📋 DNS Servers (one per line):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15,5))
        self.dns_text = ctk.CTkTextbox(list_frame, height=150, font=ctk.CTkFont(size=11))
        self.dns_text.pack(fill="x", padx=20, pady=5)
        # Pre-populate with common DNS
        default_dns = """1.1.1.1 (Cloudflare)
8.8.8.8 (Google)
9.9.9.9 (Quad9)
208.67.222.222 (OpenDNS)
94.140.14.14 (AdGuard)
78.157.42.100 (Electro)
178.22.122.100 (Shecan)
10.202.10.10 (Radar)"""
        self.dns_text.insert("1.0", default_dns)
        
        # Settings
        settings_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        settings_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(settings_frame, text="⚙️ Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15,5))
        
        # Threads
        self.lbl_threads = ctk.CTkLabel(settings_frame, text="Threads: 20")
        self.lbl_threads.pack(anchor="w", padx=20)
        self.threads_slider = ctk.CTkSlider(settings_frame, from_=5, to=100, number_of_steps=19, progress_color=CF_ORANGE, command=lambda v: self.lbl_threads.configure(text=f"Threads: {int(v)}"))
        self.threads_slider.set(20)
        self.threads_slider.pack(fill="x", padx=20, pady=5)
        
        # Timeout
        self.lbl_timeout = ctk.CTkLabel(settings_frame, text="Timeout: 2.0s")
        self.lbl_timeout.pack(anchor="w", padx=20)
        self.timeout_slider = ctk.CTkSlider(settings_frame, from_=0.5, to=10.0, number_of_steps=19, progress_color="#29B6F6", command=lambda v: self.lbl_timeout.configure(text=f"Timeout: {float(v):.1f}s"))
        self.timeout_slider.set(2.0)
        self.timeout_slider.pack(fill="x", padx=20, pady=5)
        
        # Test domain
        domain_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        domain_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(domain_frame, text="🌍 Test Domain:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15,5))
        self.domain_entry = ctk.CTkEntry(domain_frame, placeholder_text="google.com", width=300)
        self.domain_entry.pack(anchor="w", padx=20, pady=5)
        self.domain_entry.insert(0, "google.com")
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        btn_frame.grid_columnconfigure((0,1,2), weight=1)
        
        self.start_btn = ctk.CTkButton(btn_frame, text="▶ START SCAN", fg_color=CF_ORANGE, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.start_scan)
        self.start_btn.grid(row=0, column=0, padx=10, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ STOP", fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(weight="bold"), state="disabled", command=self.stop_scan)
        self.stop_btn.grid(row=0, column=1, padx=10, sticky="ew")
        
        self.export_btn = ctk.CTkButton(btn_frame, text="📁 Export Results", fg_color="#2E7D32", hover_color="#1B5E20", command=self.export_results)
        self.export_btn.grid(row=0, column=2, padx=10, sticky="ew")
        
        # Progress
        self.progress_bar = ctk.CTkProgressBar(scroll, progress_color=CF_ORANGE)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(scroll, text="Ready", text_color="gray")
        self.status_label.pack(pady=5)
        
        # Results table
        self.results_text = ctk.CTkTextbox(scroll, height=300, font=ctk.CTkFont(family="Consolas", size=11))
        self.results_text.pack(fill="both", expand=True, pady=10)
    
    def parse_dns_list(self):
        text = self.dns_text.get("1.0", "end-1c").strip()
        dns_list = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract IP (ignore comments after space)
                ip = line.split()[0] if ' ' in line else line
                dns_list.append(ip)
        return dns_list
    
    def log(self, msg):
        self.parent.after(0, lambda: self.results_text.insert("end", msg + "\n"))
        self.parent.after(0, lambda: self.results_text.see("end"))
    
    def scan_single_dns(self, dns, domain, timeout):
        start = time.time()
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            answers = resolver.resolve(domain, 'A')
            latency = int((time.time() - start) * 1000)
            # Check DNSSEC
            dnssec_ok = False
            try:
                if answers.response.flags & dns.flags.AD:
                    dnssec_ok = True
            except:
                pass
            return {"dns": dns, "latency": latency, "status": "OK", "dnssec": dnssec_ok, "ip": str(answers[0])}
        except dns.resolver.NXDOMAIN:
            return {"dns": dns, "latency": 9999, "status": "NXDOMAIN", "dnssec": False, "ip": ""}
        except dns.resolver.Timeout:
            return {"dns": dns, "latency": 9999, "status": "TIMEOUT", "dnssec": False, "ip": ""}
        except Exception as e:
            return {"dns": dns, "latency": 9999, "status": f"ERROR", "dnssec": False, "ip": ""}
    
    def start_scan(self):
        dns_list = self.parse_dns_list()
        if not dns_list:
            messagebox.showerror("Error", "Please enter at least one DNS server!")
            return
        
        domain = self.domain_entry.get().strip()
        if not domain:
            messagebox.showerror("Error", "Please enter a test domain!")
            return
        
        self.scan_stop_flag = False
        self.results = []
        self.results_text.delete("1.0", "end")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="Scanning...", text_color=CF_ORANGE)
        
        threading.Thread(target=self._scan_thread, args=(dns_list, domain), daemon=True).start()
    
    def _scan_thread(self, dns_list, domain):
        timeout = self.timeout_slider.get()
        threads = int(self.threads_slider.get())
        total = len(dns_list)
        completed = 0
        results = []
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.scan_single_dns, dns, domain, timeout): dns for dns in dns_list}
            for future in futures:
                if self.scan_stop_flag:
                    break
                res = future.result()
                results.append(res)
                completed += 1
                progress = completed / total
                self.parent.after(0, lambda p=progress: self.progress_bar.set(p))
                self.parent.after(0, lambda c=completed, t=total: self.status_label.configure(text=f"Progress: {c}/{t}"))
        
        # Sort by latency
        results.sort(key=lambda x: x['latency'])
        self.results = results
        
        # Display results
        self.parent.after(0, lambda: self.results_text.delete("1.0", "end"))
        output = "📊 DNS SCAN RESULTS\n" + "="*70 + "\n"
        output += f"{'DNS Server':<20} {'Latency':<10} {'Status':<12} {'DNSSEC':<8} {'Resolved IP':<15}\n"
        output += "-"*70 + "\n"
        for r in results:
            latency_str = f"{r['latency']}ms" if r['latency'] < 9999 else "Timeout"
            dnssec_str = "✅" if r['dnssec'] else "❌"
            output += f"{r['dns']:<20} {latency_str:<10} {r['status']:<12} {dnssec_str:<8} {r['ip']:<15}\n"
        output += "="*70 + f"\n✅ Best DNS: {results[0]['dns']} ({results[0]['latency']}ms)"
        
        self.parent.after(0, lambda: self.results_text.insert("1.0", output))
        self.parent.after(0, lambda: self.start_btn.configure(state="normal"))
        self.parent.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.parent.after(0, lambda: self.status_label.configure(text="Scan completed", text_color="#66BB6A"))
    
    def stop_scan(self):
        self.scan_stop_flag = True
        self.status_label.configure(text="Stopping...", text_color="#FFA726")
    
    def export_results(self):
        if not self.results:
            messagebox.showwarning("Warning", "No results to export!")
            return
        from tkinter import filedialog
        import json
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            messagebox.showinfo("Success", f"Results saved to {file_path}")
