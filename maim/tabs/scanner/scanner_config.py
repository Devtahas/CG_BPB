# tabs/scanner/scanner_config.py
import json
import os
import base64
import urllib.parse
from tabs.crypto_manager import storage_crypto
from .scanner_utils import ScannerUtils


class ScannerConfig:
    """تولید کانفیگ‌های نهایی و فایل سابسکریپشن"""

    def __init__(self, configs_dir, subs_dir):
        self.configs_dir = configs_dir
        self.subs_dir = subs_dir

    def generate_final_configs(self, best_pairs, var_tls, var_none, var_h2, var_http1,
                               var_ws, var_grpc, var_tcp, var_frag_enable, fragment_settings,
                               entry_uuid, entry_host, entry_path, log_callback):
        """تولید کانفیگ‌های نهایی از IPهای پیدا شده"""

        if not best_pairs:
            log_callback("\n❌ Process stopped. No working IPs found.")
            return [], 0

        sorted_best = sorted(best_pairs, key=lambda x: (x.get('dl', 0), -x.get('ping', 9999)), reverse=True)
        sorted_best = sorted_best[:15]

        log_callback(f"\n🌍 Filtering applied! Generating configs for the TOP {len(sorted_best)} best IPs...")
        ip_countries_map = ScannerUtils.get_countries_batch([d['ip'] for d in sorted_best])

        vless_links = []
        global_index = 1

        gen_tls = var_tls.get() == 1
        gen_none = var_none.get() == 1
        gen_h2 = var_h2.get() == 1
        gen_http1 = var_http1.get() == 1

        net_types = []
        if var_ws.get() == 1:
            net_types.append("ws")
        if var_grpc.get() == 1:
            net_types.append("grpc")
        if var_tcp.get() == 1:
            net_types.append("tcp")

        for data in sorted_best:
            ip, port = data['ip'], int(data['port'])
            sec = "none" if port in [80, 8080, 8880, 2052, 2082, 2095] else "tls"
            cc = ip_countries_map.get(ip, "UNK")
            dl_speed = data.get('dl', 0)

            if sec == "tls" and not gen_tls:
                continue
            if sec == "none" and not gen_none:
                continue

            alpns = []
            if sec == "tls":
                if gen_http1:
                    alpns.append("http/1.1")
                if gen_h2:
                    alpns.append("h2,http/1.1")
            else:
                alpns = [""]

            for alpn in alpns:
                for net_type in net_types:
                    self._create_config_json(data, global_index, alpn, cc, sec, net_type,
                                            entry_uuid, entry_host, entry_path, var_frag_enable, fragment_settings)

                    alpn_lbl = "H2" if "h2" in alpn else ("HTTP1" if alpn else "None")
                    alias = f"🌍{cc} | {ip}:{port} | {sec.upper()} | {net_type.upper()} | DL:{dl_speed}K"

                    sec_param = f"&security=tls&alpn={urllib.parse.quote(alpn)}&sni={entry_host}" if sec == "tls" else "&security=none"

                    path = entry_path
                    if not path.startswith("/"):
                        path = "/" + path

                    net_params = f"&type={net_type}"
                    if net_type == "ws":
                        net_params += f"&host={entry_host}&path={urllib.parse.quote(path)}"
                    elif net_type == "grpc":
                        svc_name = path.lstrip("/")
                        net_params += f"&serviceName={urllib.parse.quote(svc_name)}&mode=multi"
                    elif net_type == "tcp":
                        net_params += f"&headerType=http&host={entry_host}&path={urllib.parse.quote(path)}"

                    if var_frag_enable.get() == 1:
                        packet_val = fragment_settings['packets']
                        length_val = fragment_settings['length']
                        interval_val = fragment_settings['interval']
                        frag_param = f"&fragment={urllib.parse.quote(f'{packet_val},{length_val},{interval_val}')}"
                        net_params += frag_param

                    vless_link = (f"vless://{entry_uuid}@{ip}:{port}?encryption=none"
                                  f"{net_params}&fp=chrome{sec_param}#{urllib.parse.quote(alias)}")
                    vless_links.append(vless_link)
                    global_index += 1

        # ذخیره سابسکریپشن (فایل متنی - در صورت نیاز رمزنگاری شود)
        sub_path = os.path.join(self.subs_dir, "sub.txt")
        try:
            sub_content = base64.b64encode("\n".join(vless_links).encode()).decode()
            # استفاده از safe_open برای نوشتن امن
            with storage_crypto.safe_open(sub_path, 'w', encoding='utf-8') as f:
                f.write(sub_content)
        except:
            pass

        log_callback(f"\n🎉 ALL DONE! Generated {len(vless_links)} configs from top IPs.")
        return vless_links, len(best_pairs)

    def _create_config_json(self, data, index, alpn, cc, sec, net_type,
                           entry_uuid, entry_host, entry_path, var_frag_enable, fragment_settings):
        """ساخت فایل JSON کانفیگ و ذخیره با رمزنگاری"""
        alpn_lbl = "H2" if "h2" in alpn else ("HTTP1" if alpn else "None")
        path = entry_path
        if not path.startswith("/"):
            path = "/" + path

        stream_settings = {
            "network": net_type,
            "security": sec,
            "sockopt": {"domainStrategy": "UseIP", "tcpFastOpen": True}
        }

        if var_frag_enable.get() == 1:
            stream_settings["sockopt"]["fragment"] = fragment_settings

        if net_type == "ws":
            stream_settings["wsSettings"] = {"host": entry_host, "path": path}
        elif net_type == "grpc":
            stream_settings["grpcSettings"] = {"serviceName": path.lstrip("/"), "multiMode": False}
        elif net_type == "tcp":
            stream_settings["tcpSettings"] = {
                "header": {
                    "type": "http",
                    "request": {
                        "path": [path],
                        "headers": {"Host": [entry_host]}
                    }
                }
            }

        if sec == "tls" and alpn:
            stream_settings["tlsSettings"] = {
                "serverName": entry_host,
                "alpn": alpn.split(","),
                "fingerprint": "chrome"
            }

        config = {
            "remarks": f"🌍{cc} | {data['ip']}:{data['port']} | {net_type.upper()} | {alpn_lbl} | DL:{data.get('dl', 0)}K | {sec.upper()}",
            "dns": {"servers": [{"address": data['dns_ip'], "tag": "remote-dns"}]},
            "inbounds": [{
                "listen": "127.0.0.1", "port": 10808, "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {"destOverride": ["http", "tls"], "enabled": True, "routeOnly": True}
            }],
            "outbounds": [
                {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [{
                            "address": data['ip'],
                            "port": data['port'],
                            "users": [{"id": entry_uuid, "encryption": "none"}]
                        }]
                    },
                    "streamSettings": stream_settings
                },
                {"protocol": "dns", "tag": "dns-out"},
                {"protocol": "freedom", "tag": "direct"}
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {"inboundTag": ["remote-dns"], "outboundTag": "proxy", "type": "field"},
                    {"network": "tcp", "outboundTag": "proxy", "type": "field"}
                ]
            }
        }

        safe_ip = data['ip'].replace(':', '_')
        filename = f"Config_{index}_{cc}_{sec}_{net_type}_{alpn_lbl}_{data['port']}_{safe_ip}.json"
        filepath = os.path.join(self.configs_dir, filename)
        try:
            # ذخیره با رمزنگاری
            storage_crypto.save_json(filepath, config)
        except:
            pass
