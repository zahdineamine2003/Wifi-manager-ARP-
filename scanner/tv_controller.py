"""
Module pour contrôler les Smart TVs sur le réseau.
Supporte Samsung, LG, Sony, et autres via différents protocoles.
"""

import socket
import struct
import time
import requests
from typing import Optional, Dict, List


class TVController:
    """Contrôleur universel pour Smart TVs."""
    
    def __init__(self):
        """Initialise le contrôleur."""
        self.detected_tvs = []
    
    def send_wake_on_lan(self, mac_address: str) -> bool:
        """
        Envoie un paquet Wake-on-LAN pour allumer un appareil.
        
        Args:
            mac_address: Adresse MAC de la TV
            
        Returns:
            True si envoyé avec succès
        """
        try:
            print(f"[TV] Envoi Wake-on-LAN à {mac_address}")
            
            # Convertit MAC en bytes
            mac_bytes = bytes.fromhex(mac_address.replace(':', '').replace('-', ''))
            
            # Crée le magic packet (6x FF + 16x MAC)
            magic_packet = b'\xff' * 6 + mac_bytes * 16
            
            # Envoie en broadcast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('<broadcast>', 9))
            sock.close()
            
            print(f"[TV] ✓ Wake-on-LAN envoyé")
            return True
            
        except Exception as e:
            print(f"[TV] Erreur Wake-on-LAN: {e}")
            return False
    
    def detect_tv_brand(self, ip: str, mac: str, vendor: str) -> str:
        """
        Détecte la marque de la TV.
        
        Args:
            ip: Adresse IP
            mac: Adresse MAC
            vendor: Nom du vendeur OUI
            
        Returns:
            Marque détectée
        """
        vendor_lower = vendor.lower()
        
        if 'samsung' in vendor_lower:
            return 'Samsung'
        elif 'lg' in vendor_lower:
            return 'LG'
        elif 'sony' in vendor_lower:
            return 'Sony'
        elif 'philips' in vendor_lower:
            return 'Philips'
        elif 'panasonic' in vendor_lower:
            return 'Panasonic'
        elif 'toshiba' in vendor_lower:
            return 'Toshiba'
        elif 'sharp' in vendor_lower:
            return 'Sharp'
        else:
            # Tente de détecter via ports ouverts
            if self._check_port(ip, 8001):  # Samsung
                return 'Samsung'
            elif self._check_port(ip, 3000):  # LG
                return 'LG'
            elif self._check_port(ip, 20060):  # Sony Bravia
                return 'Sony'
            return 'Unknown'
    
    def _check_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Vérifie si un port est ouvert."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def samsung_send_key(self, ip: str, key: str) -> bool:
        """
        Envoie une commande à une Samsung Smart TV.
        
        Args:
            ip: IP de la TV
            key: Touche à envoyer (KEY_POWER, KEY_VOLUP, etc.)
            
        Returns:
            True si succès
        """
        try:
            import base64
            
            print(f"[TV] Samsung: Envoi de {key} vers {ip}")
            
            # Configuration Samsung
            port = 8001
            app_name = "WiFi_Manager"
            
            # Encode le nom de l'app
            app_name_b64 = base64.b64encode(app_name.encode()).decode()
            
            # URL de l'API Samsung
            url = f"http://{ip}:{port}/api/v2/channels/samsung.remote.control"
            
            # Payload
            payload = {
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Click",
                    "DataOfCmd": key,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey"
                }
            }
            
            # Headers
            headers = {
                'Content-Type': 'application/json'
            }
            
            # Envoie la requête
            response = requests.post(url, json=payload, headers=headers, timeout=3)
            
            if response.status_code == 200:
                print(f"[TV] ✓ Commande Samsung envoyée")
                return True
            else:
                print(f"[TV] Erreur Samsung: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[TV] Erreur Samsung: {e}")
            return False
    
    def lg_send_key(self, ip: str, key: str) -> bool:
        """
        Envoie une commande à une LG Smart TV (WebOS).
        
        Args:
            ip: IP de la TV
            key: Touche à envoyer
            
        Returns:
            True si succès
        """
        try:
            print(f"[TV] LG: Envoi de {key} vers {ip}")
            
            # LG WebOS utilise le port 3000
            port = 3000
            
            # Commandes LG WebOS
            commands = {
                'POWER': 'ssap://system/turnOff',
                'VOLUP': 'ssap://audio/volumeUp',
                'VOLDOWN': 'ssap://audio/volumeDown',
                'MUTE': 'ssap://audio/setMute',
                'CHANUP': 'ssap://tv/channelUp',
                'CHANDOWN': 'ssap://tv/channelDown',
            }
            
            cmd = commands.get(key, key)
            
            # WebSocket ou HTTP selon la version
            url = f"http://{ip}:{port}/api/control/{cmd}"
            
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                print(f"[TV] ✓ Commande LG envoyée")
                return True
            else:
                print(f"[TV] Erreur LG: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[TV] Erreur LG: {e}")
            return False
    
    def sony_send_key(self, ip: str, key: str) -> bool:
        """
        Envoie une commande à une Sony Bravia TV.
        
        Args:
            ip: IP de la TV
            key: Touche à envoyer
            
        Returns:
            True si succès
        """
        try:
            print(f"[TV] Sony: Envoi de {key} vers {ip}")
            
            # Sony Bravia utilise le port 80
            port = 80
            
            # IRCC codes pour Sony
            ircc_codes = {
                'POWER': 'AAAAAQAAAAEAAAAVAw==',
                'VOLUP': 'AAAAAQAAAAEAAAASAw==',
                'VOLDOWN': 'AAAAAQAAAAEAAAATAw==',
                'MUTE': 'AAAAAQAAAAEAAAAUAw==',
                'CHANUP': 'AAAAAQAAAAEAAAAQAw==',
                'CHANDOWN': 'AAAAAQAAAAEAAAARAw==',
            }
            
            ircc = ircc_codes.get(key, '')
            if not ircc:
                print(f"[TV] Commande Sony inconnue: {key}")
                return False
            
            # URL IRCC
            url = f"http://{ip}/sony/ircc"
            
            # SOAP payload
            payload = f'''<?xml version="1.0"?>
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                <s:Body>
                    <u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">
                        <IRCCCode>{ircc}</IRCCCode>
                    </u:X_SendIRCC>
                </s:Body>
            </s:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset=UTF-8',
                'SOAPACTION': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'
            }
            
            response = requests.post(url, data=payload, headers=headers, timeout=3)
            
            if response.status_code == 200:
                print(f"[TV] ✓ Commande Sony envoyée")
                return True
            else:
                print(f"[TV] Erreur Sony: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[TV] Erreur Sony: {e}")
            return False
    
    def universal_send_key(self, ip: str, mac: str, brand: str, key: str) -> bool:
        """
        Envoie une commande universelle selon la marque.
        
        Args:
            ip: IP de la TV
            mac: MAC de la TV
            brand: Marque de la TV
            key: Touche à envoyer
            
        Returns:
            True si succès
        """
        print(f"[TV] Envoi commande {key} vers {brand} TV ({ip})")
        
        if key == 'POWER_ON':
            # Wake-on-LAN pour allumer
            return self.send_wake_on_lan(mac)
        
        # Envoie selon la marque
        if brand == 'Samsung':
            # Samsung utilise KEY_ prefix
            samsung_key = f"KEY_{key}"
            return self.samsung_send_key(ip, samsung_key)
        elif brand == 'LG':
            return self.lg_send_key(ip, key)
        elif brand == 'Sony':
            return self.sony_send_key(ip, key)
        else:
            # Essaie toutes les méthodes
            print(f"[TV] Marque inconnue, tentative de toutes les méthodes...")
            
            results = []
            results.append(self.samsung_send_key(ip, f"KEY_{key}"))
            results.append(self.lg_send_key(ip, key))
            results.append(self.sony_send_key(ip, key))
            
            return any(results)
    
    def get_available_commands(self) -> List[str]:
        """Retourne la liste des commandes disponibles."""
        return [
            'POWER_ON',    # Allumer (WoL)
            'POWER',       # Éteindre
            'VOLUP',       # Volume +
            'VOLDOWN',     # Volume -
            'MUTE',        # Muet
            'CHANUP',      # Chaîne +
            'CHANDOWN',    # Chaîne -
            'HOME',        # Menu principal
            'BACK',        # Retour
            'ENTER',       # Entrer
            'UP',          # Haut
            'DOWN',        # Bas
            'LEFT',        # Gauche
            'RIGHT',       # Droite
        ]
