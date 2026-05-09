# tabs/client/client_utils.py
import socket
import time
import json
import urllib.parse
import base64
from config import CF_ORANGE, CF_ORANGE_HOVER, BG_PANEL, storage_crypto
from tabs.crypto_manager import storage_crypto


class ClientUtils:
    """توابع کمکی کلاینت - پینگ، پرچم، تبدیل لینک و..."""

    @staticmethod
    def get_flag_emoji(country_code):
        """دریافت ایموجی پرچم بر اساس کد کشور"""
        if not country_code or len(country_code) != 2:
            return "🌍"
        return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)

    @staticmethod
    def ping_config(path, callback):
        """پینگ کردن یک کانفیگ و برگرداندن نتیجه (با پشتیبانی از رمزنگاری)"""
        try:
            # بارگذاری با رمزنگاری (fallback به فایل معمولی)
            data = storage_crypto.load_json(path)
            if data is None:
                # تلاش برای بارگذاری از فایل معمولی (برای مهاجرت)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # رمزنگاری و ذخیره مجدد
                    storage_crypto.save_json(path, data)

            outbound = data.get("outbounds", [])[0]
            protocol = outbound.get("protocol", "").lower()

            address = None
            port = None

            if protocol in ["vless", "vmess"]:
                vnext = outbound.get("settings", {}).get("vnext", [])[0]
                if vnext:
                    address = vnext.get("address", "")
                    port = int(vnext.get("port", 443))

            elif protocol in ["shadowsocks", "trojan"]:
                servers = outbound.get("settings", {}).get("servers", [])[0]
                if servers:
                    address = servers.get("address", "")
                    port = int(servers.get("port", 443))

            elif protocol == "wireguard":
                address = outbound.get("settings", {}).get("address", "10.0.0.2")
                port = int(outbound.get("settings", {}).get("port", 51820))

            elif protocol == "socks":
                servers = outbound.get("settings", {}).get("servers", [])[0]
                if servers:
                    address = servers.get("address", "")
                    port = int(servers.get("port", 1080))

            elif protocol == "http":
                servers = outbound.get("settings", {}).get("servers", [])[0]
                if servers:
                    address = servers.get("address", "")
                    port = int(servers.get("port", 8080))

            elif protocol in ["tuic", "hysteria2", "quic"]:
                address = outbound.get("settings", {}).get("address", "")
                port = int(outbound.get("settings", {}).get("port", 443))

            if not address or not port:
                callback(path, "Skip", "gray")
                return

            start_time = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.5)
                s.connect((address, port))
            ping_ms = int((time.time() - start_time) * 1000)

            if ping_ms < 200:
                color = "#66BB6A"
            elif ping_ms < 500:
                color = "#FFA726"
            else:
                color = "#EF5350"
            callback(path, f"{ping_ms} ms", color)
        except socket.timeout:
            callback(path, "Timeout", "#EF5350")
        except Exception:
            callback(path, "Error", "#EF5350")

    @staticmethod
    def detect_protocol(link):
        """تشخیص نوع پروتکل از روی لینک"""
        if link.startswith("vless://"):
            return "vless"
        elif link.startswith("vmess://"):
            return "vmess"
        elif link.startswith("ss://"):
            return "shadowsocks"
        elif link.startswith("trojan://"):
            return "trojan"
        elif link.startswith("hy2://") or link.startswith("hysteria2://"):
            return "hysteria2"
        elif link.startswith("tuic://"):
            return "tuic"
        elif link.startswith("wireguard://"):
            return "wireguard"
        elif link.startswith("socks4://") or link.startswith("socks5://"):
            return "socks"
        elif link.startswith("http://") or link.startswith("https://"):
            return "http"
        elif link.startswith("ssh://"):
            return "ssh"
        elif link.startswith("openvpn://"):
            return "openvpn"
        elif link.startswith("quic://"):
            return "quic"
        else:
            return "unknown"

    @staticmethod
    def convert_to_json(link):
        """تبدیل لینک هر پروتکلی به JSON کانفیگ Xray-core"""
        protocol = ClientUtils.detect_protocol(link)

        if protocol == "vless":
            return ClientUtils._convert_vless_to_json(link)
        elif protocol == "vmess":
            return ClientUtils._convert_vmess_to_json(link)
        elif protocol == "shadowsocks":
            return ClientUtils._convert_ss_to_json(link)
        elif protocol == "trojan":
            return ClientUtils._convert_trojan_to_json(link)
        elif protocol == "hysteria2":
            return ClientUtils._convert_hysteria2_to_json(link)
        elif protocol == "tuic":
            return ClientUtils._convert_tuic_to_json(link)
        elif protocol == "wireguard":
            return ClientUtils._convert_wireguard_to_json(link)
        elif protocol == "socks":
            return ClientUtils._convert_socks_to_json(link)
        elif protocol == "http":
            return ClientUtils._convert_http_to_json(link)
        else:
            raise Exception(f"Unsupported protocol: {protocol}")

    @staticmethod
    def _convert_vless_to_json(link):
        """تبدیل لینک VLESS به JSON"""
        rest = link[8:]
        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported VLESS Config"

        if "?" in rest:
            rest, query_str = rest.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))
        else:
            params = {}

        uuid_str, server_port = rest.split("@", 1)
        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 443

        config = {
            "remarks": f"📥 VLESS - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "vless",
                    "settings": {
                        "vnext": [{
                            "address": server, "port": port,
                            "users": [{"id": uuid_str, "encryption": "none", "flow": params.get("flow", "")}]
                        }]
                    },
                    "streamSettings": {"network": params.get("type", "tcp"), "security": params.get("security", "none")}
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        net_type = params.get("type", "tcp")
        if net_type == "ws":
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "path": params.get("path", "/"),
                "headers": {"Host": params.get("host", server)}
            }
        elif net_type == "grpc":
            config["outbounds"][0]["streamSettings"]["grpcSettings"] = {
                "serviceName": params.get("serviceName", ""),
                "multiMode": params.get("mode", "multi") == "multi"
            }

        sec_type = params.get("security", "none")
        if sec_type == "tls":
            alpn = params.get("alpn", "").split(",") if params.get("alpn") else []
            config["outbounds"][0]["streamSettings"]["tlsSettings"] = {
                "serverName": params.get("sni", server),
                "fingerprint": params.get("fp", "chrome"),
                "alpn": [a for a in alpn if a]
            }
        elif sec_type == "reality":
            config["outbounds"][0]["streamSettings"]["realitySettings"] = {
                "publicKey": params.get("pbk", ""),
                "shortId": params.get("sid", ""),
                "serverName": params.get("sni", server),
                "fingerprint": params.get("fp", "chrome"),
                "spiderX": params.get("spx", "/")
            }

        return config

    @staticmethod
    def _convert_vmess_to_json(link):
        """تبدیل لینک VMESS به JSON"""
        encoded = link[8:]
        if "#" in encoded:
            encoded, remarks = encoded.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported VMESS Config"

        try:
            decoded = base64.b64decode(encoded).decode('utf-8')
            vmess_data = json.loads(decoded)
        except:
            raise Exception("Invalid VMESS link format")

        config = {
            "remarks": f"📥 VMESS - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "vmess",
                    "settings": {
                        "vnext": [{
                            "address": vmess_data.get("add", ""),
                            "port": int(vmess_data.get("port", 443)),
                            "users": [{
                                "id": vmess_data.get("id", ""),
                                "security": vmess_data.get("scy", "auto"),
                                "alterId": int(vmess_data.get("aid", 0))
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": vmess_data.get("net", "tcp"),
                        "security": vmess_data.get("tls", "none")
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        net_type = vmess_data.get("net", "tcp")
        if net_type == "ws":
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "path": vmess_data.get("path", "/"),
                "headers": {"Host": vmess_data.get("host", vmess_data.get("add", ""))}
            }
        elif net_type == "grpc":
            config["outbounds"][0]["streamSettings"]["grpcSettings"] = {
                "serviceName": vmess_data.get("path", "").lstrip("/"),
                "multiMode": False
            }

        if vmess_data.get("tls", "none") == "tls":
            config["outbounds"][0]["streamSettings"]["tlsSettings"] = {
                "serverName": vmess_data.get("sni", vmess_data.get("add", "")),
                "fingerprint": "chrome"
            }

        return config

    @staticmethod
    def _convert_ss_to_json(link):
        """تبدیل لینک Shadowsocks به JSON"""
        encoded = link[5:]
        if "#" in encoded:
            encoded, remarks = encoded.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported Shadowsocks Config"

        try:
            decoded = base64.b64decode(encoded).decode('utf-8')
            if "@" in decoded:
                auth, server_port = decoded.split("@", 1)
                method, password = auth.split(":", 1)
                server, port = server_port.split(":", 1)
                port = int(port)
            else:
                raise Exception("Invalid SS format")
        except:
            if "@" in encoded:
                auth, server_port = encoded.split("@", 1)
                method, password = auth.split(":", 1)
                server, port = server_port.split(":", 1)
                port = int(port)
            else:
                raise Exception("Invalid SS link format")

        config = {
            "remarks": f"📥 Shadowsocks - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "shadowsocks",
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": port,
                            "method": method,
                            "password": password
                        }]
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        return config

    @staticmethod
    def _convert_trojan_to_json(link):
        """تبدیل لینک Trojan به JSON"""
        rest = link[9:]
        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported Trojan Config"

        if "?" in rest:
            rest, query_str = rest.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))
        else:
            params = {}

        password, server_port = rest.split("@", 1)
        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 443

        config = {
            "remarks": f"📥 Trojan - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "trojan",
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": port,
                            "password": password
                        }]
                    },
                    "streamSettings": {
                        "network": params.get("type", "tcp"),
                        "security": "tls"
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        net_type = params.get("type", "tcp")
        if net_type == "ws":
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "path": params.get("path", "/"),
                "headers": {"Host": params.get("host", server)}
            }

        config["outbounds"][0]["streamSettings"]["tlsSettings"] = {
            "serverName": params.get("sni", server),
            "fingerprint": params.get("fp", "chrome")
        }

        return config

    @staticmethod
    def _convert_hysteria2_to_json(link):
        """تبدیل لینک Hysteria2 به JSON"""
        rest = link[5:] if link.startswith("hy2://") else link[12:]
        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported Hysteria2 Config"

        if "?" in rest:
            rest, query_str = rest.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))
        else:
            params = {}

        if "@" in rest:
            auth, server_port = rest.split("@", 1)
            password = auth
        else:
            server_port = rest
            password = ""

        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 443

        config = {
            "remarks": f"📥 Hysteria2 - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "hysteria2",
                    "settings": {
                        "address": server,
                        "port": port,
                        "password": password
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        if params.get("sni"):
            config["outbounds"][0]["settings"]["sni"] = params.get("sni")

        return config

    @staticmethod
    def _convert_tuic_to_json(link):
        """تبدیل لینک TUIC به JSON"""
        rest = link[7:]
        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported TUIC Config"

        if "?" in rest:
            rest, query_str = rest.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))
        else:
            params = {}

        if "@" in rest:
            uuid, server_port = rest.split("@", 1)
        else:
            server_port = rest
            uuid = ""

        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 443

        config = {
            "remarks": f"📥 TUIC - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "tuic",
                    "settings": {
                        "address": server,
                        "port": port,
                        "uuid": uuid,
                        "password": params.get("password", ""),
                        "congestion_control": params.get("congestion", "bbr")
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        if params.get("sni"):
            config["outbounds"][0]["settings"]["sni"] = params.get("sni")

        return config

    @staticmethod
    def _convert_wireguard_to_json(link):
        """تبدیل لینک WireGuard به JSON"""
        rest = link[12:]
        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported WireGuard Config"

        if "?" in rest:
            rest, query_str = rest.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))
        else:
            params = {}

        if "@" in rest:
            server_key, server_port = rest.split("@", 1)
        else:
            server_port = rest
            server_key = ""

        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 51820

        config = {
            "remarks": f"📥 WireGuard - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "wireguard",
                    "settings": {
                        "address": params.get("address", "10.0.0.2/32"),
                        "private_key": params.get("private_key", ""),
                        "peers": [{
                            "address": server,
                            "port": port,
                            "public_key": server_key
                        }]
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        return config

    @staticmethod
    def _convert_socks_to_json(link):
        """تبدیل لینک SOCKS به JSON"""
        protocol_type = "socks5" if link.startswith("socks5://") else "socks4"
        rest = link[9:] if protocol_type == "socks5" else link[8:]

        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = f"Imported {protocol_type.upper()} Config"

        username = ""
        password = ""

        if "@" in rest:
            auth, server_port = rest.split("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
            else:
                username = auth
                password = ""
        else:
            server_port = rest

        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 1080

        config = {
            "remarks": f"📥 {protocol_type.upper()} - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "socks",
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": port,
                            "users": [{"user": username, "pass": password}] if username else []
                        }]
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        return config

    @staticmethod
    def _convert_http_to_json(link):
        """تبدیل لینک HTTP/HTTPS Proxy به JSON"""
        rest = link[7:] if link.startswith("http://") else link[8:]

        if "#" in rest:
            rest, remarks = rest.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "Imported HTTP Config"

        username = ""
        password = ""

        if "@" in rest:
            auth, server_port = rest.split("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
            else:
                username = auth
                password = ""
        else:
            server_port = rest

        if ":" in server_port:
            server, port = server_port.split(":", 1)
            port = int(port)
        else:
            server, port = server_port, 8080

        config = {
            "remarks": f"📥 HTTP - {remarks}",
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [
                {
                    "tag": "proxy", "protocol": "http",
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": port,
                            "users": [{"user": username, "pass": password}] if username else []
                        }]
                    }
                },
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {"domainStrategy": "AsIs", "rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}]}
        }

        return config
