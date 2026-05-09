# tabs/gaming/gaming_ui.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import random
import psutil
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, BG_DARK

from .gaming_utils import GamingUtils
from .gaming_core import GameAccelerator, NATOptimizer, PingStabilizer
from .gaming_dns import GamingDNS


class GamingUI(ctk.CTkFrame):
    """کلاس اصلی تب Gaming"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # هسته‌ها
        self.game_accelerator = GameAccelerator()
        self.nat_optimizer = NATOptimizer()
        self.ping_stabilizer = PingStabilizer()
        self.gaming_dns = GamingDNS()
        
        # متغیرها
        self.monitor_running = False
        self.accelerator_active = False
        self.ping_active = False
        
        self.setup_ui()
        self.start_monitoring()

        # ★ پشتیبانی از پلاگین‌های دسته "gaming"
        if hasattr(self.master, "plugin_manager"):
            self.load_category_plugins("gaming")
    
    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        ctk.CTkLabel(header_frame, text="🎮 Gaming Mode", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=40)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=CF_ORANGE,
                                     segmented_button_selected_hover_color=CF_ORANGE_HOVER)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_performance = self.tabview.add("⚡ Performance")
        self.tab_network = self.tabview.add("🌐 Network")
        self.tab_dns = self.tabview.add("📡 Gaming DNS")
        
        self.setup_performance_tab()
        self.setup_network_tab()
        self.setup_dns_tab()
    
    def setup_performance_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_performance, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # System Resources
        sys_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        sys_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(sys_frame, text="💻 System Resources", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 10))
        
        cpu_frame = ctk.CTkFrame(sys_frame, fg_color="transparent")
        cpu_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(cpu_frame, text="CPU:", width=80).pack(side="left")
        self.cpu_bar = ctk.CTkProgressBar(cpu_frame, width=300, progress_color="#29B6F6")
        self.cpu_bar.pack(side="left", padx=10)
        self.cpu_label = ctk.CTkLabel(cpu_frame, text="0%", width=50)
        self.cpu_label.pack(side="left")
        
        ram_frame = ctk.CTkFrame(sys_frame, fg_color="transparent")
        ram_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(ram_frame, text="RAM:", width=80).pack(side="left")
        self.ram_bar = ctk.CTkProgressBar(ram_frame, width=300, progress_color="#AB47BC")
        self.ram_bar.pack(side="left", padx=10)
        self.ram_label = ctk.CTkLabel(ram_frame, text="0%", width=50)
        self.ram_label.pack(side="left")
        
        gpu_frame = ctk.CTkFrame(sys_frame, fg_color="transparent")
        gpu_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(gpu_frame, text="GPU:", width=80).pack(side="left")
        self.gpu_bar = ctk.CTkProgressBar(gpu_frame, width=300, progress_color="#FFA726")
        self.gpu_bar.pack(side="left", padx=10)
        self.gpu_label = ctk.CTkLabel(gpu_frame, text="0%", width=50)
        self.gpu_label.pack(side="left")
        
        # Game Accelerator
        acc_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        acc_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(acc_frame, text="🚀 Game Accelerator", font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15, 5))
        ctk.CTkLabel(acc_frame, text="Close background apps and optimize system for gaming", text_color="gray").pack()
        
        self.btn_accelerator = ctk.CTkButton(acc_frame, text="▶ START ACCELERATOR", fg_color="#2E7D32",
                                            hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"),
                                            command=self.toggle_accelerator)
        self.btn_accelerator.pack(pady=15)
        self.acc_status = ctk.CTkLabel(acc_frame, text="", text_color="gray")
        self.acc_status.pack(pady=(0, 15))
        
        # High Usage Processes
        proc_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        proc_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(proc_frame, text="📊 High Usage Processes", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EF5350").pack(pady=(15, 5))
        self.proc_text = ctk.CTkTextbox(proc_frame, height=120, font=ctk.CTkFont(size=12))
        self.proc_text.pack(fill="x", padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(proc_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))
        ctk.CTkButton(btn_frame, text="🔄 Refresh", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.refresh_processes).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑️ Kill Selected", fg_color="transparent", border_width=1,
                     border_color="#EF5350", text_color="#EF5350", command=self.kill_selected_process).pack(side="left", padx=5)
    
    def setup_network_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_network, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        ping_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        ping_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(ping_frame, text="📡 Ping Stabilizer (FEC)", font=ctk.CTkFont(size=16, weight="bold"), text_color="#29B6F6").pack(pady=(15, 5))
        ctk.CTkLabel(ping_frame, text="Compensate packet loss using Forward Error Correction algorithm", text_color="gray").pack()
        
        self.btn_ping = ctk.CTkButton(ping_frame, text="▶ START STABILIZER", fg_color="#2E7D32",
                                     hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"),
                                     command=self.toggle_ping_stabilizer)
        self.btn_ping.pack(pady=15)
        self.ping_status = ctk.CTkLabel(ping_frame, text="", text_color="gray")
        self.ping_status.pack(pady=(0, 15))
        
        target_frame = ctk.CTkFrame(ping_frame, fg_color="transparent")
        target_frame.pack(pady=(0, 15))
        ctk.CTkLabel(target_frame, text="Target Server:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.ping_target = ctk.CTkEntry(target_frame, width=150, placeholder_text="8.8.8.8")
        self.ping_target.insert(0, "8.8.8.8")
        self.ping_target.pack(side="left", padx=5)
        
        nat_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        nat_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(nat_frame, text="🌐 NAT Optimization", font=ctk.CTkFont(size=16, weight="bold"), text_color="#AB47BC").pack(pady=(15, 5))
        ctk.CTkLabel(nat_frame, text="Optimize NAT settings for better gaming performance", text_color="gray").pack()
        
        btn_nat_frame = ctk.CTkFrame(nat_frame, fg_color="transparent")
        btn_nat_frame.pack(pady=15)
        ctk.CTkButton(btn_nat_frame, text="⚡ OPTIMIZE NAT", fg_color=CF_ORANGE, text_color="black",
                     font=ctk.CTkFont(weight="bold"), command=self.optimize_nat).pack(side="left", padx=5)
        ctk.CTkButton(btn_nat_frame, text="🔄 RESET NAT", fg_color="transparent", border_width=1,
                     border_color="#EF5350", text_color="#EF5350", command=self.reset_nat).pack(side="left", padx=5)
        self.nat_status = ctk.CTkLabel(nat_frame, text="", text_color="gray")
        self.nat_status.pack(pady=(0, 15))
        
        net_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        net_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(net_frame, text="📊 Network Statistics", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 5))
        stats_frame = ctk.CTkFrame(net_frame, fg_color="transparent")
        stats_frame.pack(pady=10)
        
        ctk.CTkLabel(stats_frame, text="Current Ping:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.current_ping = ctk.CTkLabel(stats_frame, text="-- ms", text_color="gray")
        self.current_ping.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(stats_frame, text="Packet Loss:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.current_loss = ctk.CTkLabel(stats_frame, text="--%", text_color="gray")
        self.current_loss.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkButton(stats_frame, text="🔄 Test Now", fg_color="transparent", border_width=1,
                     border_color=CF_ORANGE, text_color=CF_ORANGE, command=self.test_network).grid(row=2, column=0, columnspan=2, pady=10)
    
    def setup_dns_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_dns, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        dns_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL, corner_radius=15)
        dns_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(dns_frame, text="🎮 Gaming DNS Servers", font=ctk.CTkFont(size=16, weight="bold"), text_color=CF_ORANGE).pack(pady=(15, 5))
        ctk.CTkLabel(dns_frame, text="DNS servers optimized for gaming (lower latency)", text_color="gray").pack()
        
        current_frame = ctk.CTkFrame(dns_frame, fg_color="transparent")
        current_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(current_frame, text="Current DNS:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.current_dns_label = ctk.CTkLabel(current_frame, text=self.gaming_dns.get_current_dns(), text_color="#29B6F6")
        self.current_dns_label.pack(side="left", padx=10)
        
        dns_list_frame = ctk.CTkFrame(dns_frame, fg_color="transparent")
        dns_list_frame.pack(fill="x", padx=20, pady=10)
        for name, dns in GamingDNS.GAMING_DNS.items():
            row_frame = ctk.CTkFrame(dns_list_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(row_frame, text=name, width=180, anchor="w").pack(side="left")
            ctk.CTkLabel(row_frame, text=f"{dns['primary']} / {dns['secondary']}", text_color="gray").pack(side="left", padx=10)
            btn = ctk.CTkButton(row_frame, text="Apply", width=60, fg_color="transparent",
                               border_width=1, border_color=CF_ORANGE, text_color=CF_ORANGE,
                               command=lambda n=name: self.apply_gaming_dns(n))
            btn.pack(side="right", padx=5)
        
        ctk.CTkButton(dns_frame, text="🔄 Reset to Automatic DNS", fg_color="transparent",
                     border_width=1, border_color="#EF5350", text_color="#EF5350",
                     command=self.reset_gaming_dns).pack(pady=15)
    
    # ========== Performance Methods (بدون ترد اضافی) ==========
    def start_monitoring(self):
        self.monitor_running = True
        self._update_resources()
        self._update_processes()
    
    def _update_resources(self):
        if not self.monitor_running:
            return
        cpu = GamingUtils.get_cpu_usage()
        ram = GamingUtils.get_ram_usage()
        gpu = GamingUtils.get_gpu_usage()
        self.cpu_bar.set(cpu / 100)
        self.cpu_label.configure(text=f"{cpu:.1f}%")
        self.ram_bar.set(ram["percent"] / 100)
        self.ram_label.configure(text=f"{ram['percent']:.1f}%")
        self.gpu_bar.set(gpu["percent"] / 100 if gpu["percent"] <= 100 else 1)
        self.gpu_label.configure(text=f"{gpu['percent']:.1f}%")
        self.after(1000, self._update_resources)
    
    def _update_processes(self):
        if not self.monitor_running:
            return
        self.refresh_processes()
        self.after(5000, self._update_processes)
    
    def refresh_processes(self):
        processes = GamingUtils.get_top_processes(8)
        self.proc_text.delete("1.0", "end")
        for proc in processes:
            cpu = proc.get('cpu_percent', 0)
            mem = proc.get('memory_percent', 0)
            line = f"{proc.get('name', 'Unknown'):<25} CPU: {cpu:.1f}%  RAM: {mem:.1f}%\n"
            self.proc_text.insert("end", line)
    
    def kill_selected_process(self):
        try:
            selected = self.proc_text.get("sel.first", "sel.last")
            if selected:
                name = selected.split()[0]
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] == name:
                            GamingUtils.kill_process(proc.info['pid'])
                            self.refresh_processes()
                            break
                    except:
                        pass
        except:
            pass
    
    def toggle_accelerator(self):
        if not self.accelerator_active:
            self.accelerator_active = True
            self.btn_accelerator.configure(text="⏹ STOP ACCELERATOR", fg_color="#C62828")
            self.acc_status.configure(text="Starting Game Accelerator...", text_color=CF_ORANGE)
            threading.Thread(target=self._run_accelerator, daemon=True).start()
        else:
            self.accelerator_active = False
            self.game_accelerator.stop_acceleration()
            self.btn_accelerator.configure(text="▶ START ACCELERATOR", fg_color="#2E7D32")
            self.acc_status.configure(text="Game Accelerator stopped", text_color="gray")
    
    def _run_accelerator(self):
        self.game_accelerator.start_acceleration(self.log_acc_status)
        self.after(0, lambda: self.acc_status.configure(text="Game Accelerator active! System optimized.", text_color="#66BB6A"))
    
    def log_acc_status(self, msg):
        self.after(0, lambda: self.acc_status.configure(text=msg, text_color=CF_ORANGE))
    
    # ========== Network Methods ==========
    def toggle_ping_stabilizer(self):
        if not self.ping_active:
            self.ping_active = True
            target = self.ping_target.get().strip() or "8.8.8.8"
            self.btn_ping.configure(text="⏹ STOP STABILIZER", fg_color="#C62828")
            self.ping_status.configure(text="Starting Ping Stabilizer...", text_color=CF_ORANGE)
            threading.Thread(target=self._run_ping_stabilizer, args=(target,), daemon=True).start()
        else:
            self.ping_active = False
            self.ping_stabilizer.stop()
            self.btn_ping.configure(text="▶ START STABILIZER", fg_color="#2E7D32")
            self.ping_status.configure(text="Ping Stabilizer stopped", text_color="gray")
    
    def _run_ping_stabilizer(self, target):
        self.ping_stabilizer.start(self.log_ping_status, target)
    
    def log_ping_status(self, msg):
        self.after(0, lambda: self.ping_status.configure(text=msg, text_color=CF_ORANGE))
    
    def optimize_nat(self):
        self.nat_status.configure(text="Optimizing NAT...", text_color=CF_ORANGE)
        threading.Thread(target=self._run_nat_optimize, daemon=True).start()
    
    def _run_nat_optimize(self):
        result = NATOptimizer.optimize(self.log_nat_status)
        if result:
            self.after(0, lambda: self.nat_status.configure(text="NAT optimized successfully!", text_color="#66BB6A"))
        else:
            self.after(0, lambda: self.nat_status.configure(text="NAT optimization failed!", text_color="#EF5350"))
    
    def reset_nat(self):
        self.nat_status.configure(text="Resetting NAT...", text_color=CF_ORANGE)
        threading.Thread(target=self._run_nat_reset, daemon=True).start()
    
    def _run_nat_reset(self):
        result = NATOptimizer.reset(self.log_nat_status)
        if result:
            self.after(0, lambda: self.nat_status.configure(text="NAT reset successfully!", text_color="#66BB6A"))
        else:
            self.after(0, lambda: self.nat_status.configure(text="NAT reset failed!", text_color="#EF5350"))
    
    def log_nat_status(self, msg):
        self.after(0, lambda: self.nat_status.configure(text=msg, text_color=CF_ORANGE))
    
    def test_network(self):
        self.current_ping.configure(text="Testing...", text_color=CF_ORANGE)
        self.current_loss.configure(text="Testing...", text_color=CF_ORANGE)
        threading.Thread(target=self._run_network_test, daemon=True).start()
    
    def _run_network_test(self):
        ping = GamingUtils.get_network_latency(count=4)
        loss = GamingUtils.get_packet_loss(count=10)
        ping_color = "#66BB6A" if ping < 50 else "#FFA726" if ping < 100 else "#EF5350"
        loss_color = "#66BB6A" if loss < 1 else "#FFA726" if loss < 5 else "#EF5350"
        self.after(0, lambda: self.current_ping.configure(text=f"{ping} ms", text_color=ping_color))
        self.after(0, lambda: self.current_loss.configure(text=f"{loss:.1f}%", text_color=loss_color))
    
    # ========== DNS Methods ==========
    def apply_gaming_dns(self, dns_name):
        self.current_dns_label.configure(text="Applying...", text_color=CF_ORANGE)
        threading.Thread(target=self._apply_dns, args=(dns_name,), daemon=True).start()
    
    def _apply_dns(self, dns_name):
        result = self.gaming_dns.set_dns(dns_name, self.log_dns_status)
        if result:
            self.after(0, lambda: self.current_dns_label.configure(text=dns_name, text_color="#66BB6A"))
        else:
            self.after(0, lambda: self.current_dns_label.configure(text="Failed", text_color="#EF5350"))
            self.after(0, lambda: self.current_dns_label.configure(text=self.gaming_dns.get_current_dns(), text_color="#29B6F6"))
    
    def reset_gaming_dns(self):
        self.current_dns_label.configure(text="Resetting...", text_color=CF_ORANGE)
        threading.Thread(target=self._reset_dns, daemon=True).start()
    
    def _reset_dns(self):
        result = self.gaming_dns.reset_dns(self.log_dns_status)
        if result:
            self.after(0, lambda: self.current_dns_label.configure(text="Automatic (DHCP)", text_color="#66BB6A"))
        else:
            self.after(0, lambda: self.current_dns_label.configure(text="Reset failed", text_color="#EF5350"))
            self.after(0, lambda: self.current_dns_label.configure(text=self.gaming_dns.get_current_dns(), text_color="#29B6F6"))
    
    def log_dns_status(self, msg):
        self.after(0, lambda: self.acc_status.configure(text=msg, text_color=CF_ORANGE))

    # ★ متد بارگذاری پلاگین‌ها
    def load_category_plugins(self, category: str):
        """تب‌های جدید برای پلاگین‌های فعال با دستهٔ مشخص شده اضافه می‌کند."""
        app = self.master
        if not hasattr(app, "plugin_manager"):
            return

        pm = app.plugin_manager
        for p in pm.get_plugins_by_category(category):
            plugin_id = p["id"]
            manifest = p["manifest"]
            tab_name = manifest.get("name", plugin_id)[:25]

            try:
                new_tab = self.tabview.add(tab_name)
            except Exception:
                new_tab = self.tabview.add(f"{tab_name}_{random.randint(0, 999)}")

            instance = pm.get_plugin_instance(plugin_id)
            if instance:
                panel = instance.get_ui_panel(new_tab)
                if panel:
                    panel.pack(fill="both", expand=True, padx=10, pady=10)
