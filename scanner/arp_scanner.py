"""
Module de scanning ARP pour découvrir les appareils sur le réseau.
Utilise Scapy pour envoyer des requêtes ARP et récolter les réponses.
"""

import threading
from typing import List, Dict, Callable, Optional
from scapy.all import ARP, Ether, srp, get_if_hwaddr
import ipaddress
import socket
import subprocess
import platform


class ARPScanner:
    """
    Classe pour effectuer des scans ARP sur un réseau.
    Exécution non-bloquante avec callback pour intégration PyQt.
    """
    
    def __init__(self, timeout: int = 3, verbose: bool = False):
        """
        Initialise le scanner ARP.
        
        Args:
            timeout: Délai d'attente en secondes pour les réponses ARP
            verbose: Mode verbose pour debug
        """
        self.timeout = timeout
        self.verbose = verbose
        self.scanning = False
        self.results = []
        self.current_thread: Optional[threading.Thread] = None
    
    def _is_valid_cidr(self, cidr: str) -> bool:
        """
        Valide si une chaîne est un CIDR valide.
        
        Args:
            cidr: Chaîne au format "192.168.1.0/24"
            
        Returns:
            True si valide, False sinon
        """
        try:
            ipaddress.IPv4Network(cidr, strict=False)
            return True
        except ValueError:
            return False
    
    def _get_local_ip(self) -> Optional[str]:
        """
        Récupère l'adresse IP locale de la machine.
        
        Returns:
            Adresse IP locale ou None
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Se connecte à 8.8.8.8:80 (n'envoie rien)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            if self.verbose:
                print(f"Erreur lors de la récupération de l'IP locale: {e}")
            return None
    
    def _perform_arp_scan(self, network: str, 
                         progress_callback: Optional[Callable] = None,
                         status_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Effectue le scan ARP sur le réseau.
        
        Args:
            network: Réseau au format CIDR
            progress_callback: Fonction appelée avec (message, count)
            status_callback: Fonction appelée avec (message)
            
        Returns:
            Liste des appareils découverts
        """
        if not self._is_valid_cidr(network):
            if status_callback:
                status_callback(f"CIDR invalide: {network}")
            return []
        
        results = []
        
        try:
            if status_callback:
                status_callback(f"Scan du réseau {network}...")
            
            if self.verbose:
                print(f"[ARP SCANNER] Scan de {network}")
            
            # Utilise ARP-scan en utilisant l'approche subprocess (cross-platform)
            results = self._perform_arp_scan_subprocess(network, progress_callback)
            
            if status_callback:
                status_callback(f"Scan terminé: {len(results)} appareils trouvés")
            
            if self.verbose:
                print(f"[ARP SCANNER] {len(results)} appareils trouvés")
            
        except PermissionError:
            if status_callback:
                status_callback("ERREUR: Permissions insuffisantes (exécutez en admin/root)")
            if self.verbose:
                print("[ARP SCANNER] Erreur: permissions insuffisantes")
        except Exception as e:
            if status_callback:
                status_callback(f"Erreur lors du scan: {str(e)}")
            if self.verbose:
                print(f"[ARP SCANNER] Erreur: {e}")
        
        return results
    
    def _perform_arp_scan_subprocess(self, network: str, 
                                     progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Effectue un scan ARP en utilisant les commandes système.
        Alternative à Scapy qui fonctionne sans WinPcap sur Windows.
        """
        results = []
        device_count = 0
        
        try:
            # Parse le réseau pour obtenir la plage d'IPs
            net = ipaddress.IPv4Network(network, strict=False)
            
            # Sur Windows: utilise arp.exe
            # Sur Linux/Mac: utilise arp-scan
            if platform.system().lower() == 'windows':
                results = self._scan_windows_arp(net, progress_callback)
            else:
                results = self._scan_linux_mac_arp(network, progress_callback)
            
        except Exception as e:
            if self.verbose:
                print(f"[ARP SCANNER] Erreur subprocess: {e}")
        
        return results
    
    def _scan_windows_arp(self, network: ipaddress.IPv4Network, 
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Scan ARP sur Windows en pingant chaque IP puis en lisant la table ARP."""
        results = []
        device_count = 0
        
        try:
            # Génère les IPs à scanner (skip le network et broadcast)
            ips_to_scan = list(network.hosts())
            
            if not ips_to_scan:
                return results
            
            # Ping de toutes les IPs en parallèle pour remplir le cache ARP
            # Utilise un pool plus large pour détecter plus d'appareils
            try:
                import concurrent.futures
                
                # Premier passage: ping rapide
                with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                    futures = {executor.submit(self._ping_host, str(ip)): ip for ip in ips_to_scan}
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()  # Get result to catch any exceptions
                        except Exception:
                            pass  # Ignore ping errors
                
                # Pause pour permettre aux appareils lents de répondre
                import time
                time.sleep(0.5)
                
                # Second passage: re-ping pour les appareils lents (TVs, mobiles en veille)
                with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
                    futures = {executor.submit(self._ping_host, str(ip)): ip for ip in ips_to_scan[::4]}
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception:
                            pass
                            
            except Exception as e:
                if self.verbose:
                    print(f"[ARP SCANNER] Erreur ping concurrent: {e}")
                # Fallback: ping séquentiel
                for ip in ips_to_scan[:50]:  # Limite à 50 pour éviter de bloquer
                    try:
                        self._ping_host(str(ip))
                    except:
                        pass
            
            # Pause supplémentaire pour permettre aux appareils lents de répondre
            import time
            time.sleep(1)
            
            # Lit la table ARP avec arp -a (multiple fois pour capturer plus d'appareils)
            try:
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
            except Exception as e:
                if self.verbose:
                    print(f"[ARP SCANNER] Erreur arp -a: {e}")
                return results
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    line = line.strip()
                    # Format Windows: "192.168.1.1 00-11-22-33-44-55 dynamic"
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            ip = parts[0]
                            mac = parts[1].replace('-', ':')
                            
                            # Valide que c'est une IP et MAC valides
                            if self._is_valid_ip(ip) and len(mac.split(':')) == 6:
                                # Vérifie que l'IP est dans le réseau
                                if ipaddress.IPv4Address(ip) in network:
                                    results.append({
                                        'ip': ip,
                                        'mac': mac,
                                        'vendor': '',
                                        'ping': None
                                    })
                                    device_count += 1
                                    if progress_callback:
                                        try:
                                            progress_callback(f"Appareil trouvé: {ip} ({mac})", device_count)
                                        except Exception:
                                            pass  # Ignore callback errors
                        except Exception:
                            pass
            
        except Exception as e:
            if self.verbose:
                print(f"[ARP SCANNER] Erreur Windows ARP: {e}")
        
        return results
    
    def _scan_linux_mac_arp(self, network: str, 
                            progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Scan ARP sur Linux/macOS en utilisant nmap ou arp-scan."""
        results = []
        device_count = 0
        
        try:
            # Essaie nmap d'abord (plus disponible)
            try:
                result = subprocess.run(
                    ['nmap', '-sn', network],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Parse la sortie nmap
                    import re
                    ips = re.findall(r'Nmap scan report for ([\d.]+)', result.stdout)
                    
                    # Pour chaque IP, cherche la MAC dans la table ARP
                    for ip in ips:
                        mac = self._get_mac_from_arp_table(ip)
                        if mac:
                            results.append({
                                'ip': ip,
                                'mac': mac,
                                'vendor': '',
                                'ping': None
                            })
                            device_count += 1
                            if progress_callback:
                                progress_callback(f"Appareil trouvé: {ip} ({mac})", device_count)
                    
                    return results
            except FileNotFoundError:
                pass
            
            # Fallback: utilise arp-scan
            result = subprocess.run(
                ['arp-scan', '-l'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            ip = parts[0].strip()
                            mac = parts[1].strip()
                            
                            if self._is_valid_ip(ip) and len(mac.split(':')) == 6:
                                results.append({
                                    'ip': ip,
                                    'mac': mac,
                                    'vendor': '',
                                    'ping': None
                                })
                                device_count += 1
                                if progress_callback:
                                    progress_callback(f"Appareil trouvé: {ip} ({mac})", device_count)
                        except:
                            pass
        
        except Exception as e:
            if self.verbose:
                print(f"[ARP SCANNER] Erreur Linux/Mac ARP: {e}")
        
        return results
    
    def _get_mac_from_arp_table(self, ip: str) -> Optional[str]:
        """Récupère la MAC d'une IP depuis la table ARP locale."""
        try:
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                import re
                match = re.search(r'([\da-f:]{17})', result.stdout)
                if match:
                    return match.group(1)
        except:
            pass
        return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Valide une adresse IP."""
        try:
            ipaddress.IPv4Address(ip)
            return True
        except:
            return False
    
    def _ping_host(self, ip: str, retries: int = 2) -> Optional[float]:
        """
        Effectue un ping vers un hôte et retourne la latence.
        
        Args:
            ip: Adresse IP à pinger
            retries: Nombre de tentatives si le premier ping échoue
            
        Returns:
            Latence en ms ou None si timeout
        """
        for attempt in range(retries):
            try:
                # Détecte le système d'exploitation
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
                
                # Exécute le ping avec timeout plus long pour les appareils lents
                result = subprocess.run(
                    ['ping', param, '1', timeout_param, str(self.timeout * 1000) if platform.system().lower() == 'windows' else str(self.timeout), ip],
                    capture_output=True,
                    timeout=self.timeout + 2
                )
                
                if result.returncode == 0:
                    # Parse la sortie pour extraire le temps
                    output = result.stdout.decode('utf-8', errors='ignore')
                    
                    if platform.system().lower() == 'windows':
                        # Windows format: "time=Xms" or "time<Xms"
                        for line in output.split('\n'):
                            if 'time' in line.lower() and 'ms' in line.lower():
                                try:
                                    # Support both "time=Xms" and "time<Xms"
                                    if '=' in line:
                                        ms = int(line.split('time=')[1].split('ms')[0].strip('<>'))
                                    elif '<' in line:
                                        ms = int(line.split('time<')[1].split('ms')[0])
                                    else:
                                        continue
                                    return float(ms)
                                except:
                                    pass
                    else:
                        # Linux/Mac format: "time=X.XXms"
                        for line in output.split('\n'):
                            if 'time=' in line:
                                try:
                                    ms = float(line.split('time=')[1].split(' ')[0])
                                    return ms
                                except:
                                    pass
                    
                    # Si on arrive ici, le ping a réussi même si on n'a pas trouvé le temps
                    return 1.0  # Retourne 1ms par défaut si le ping réussit
            
            except Exception as e:
                if self.verbose:
                    print(f"Erreur ping {ip} (tentative {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    import time
                    time.sleep(0.3)  # Pause avant retry
                    continue
        
        return None
    
    def scan(self, network: str, 
             progress_callback: Optional[Callable] = None,
             status_callback: Optional[Callable] = None,
             include_ping: bool = False) -> List[Dict]:
        """
        Lance un scan ARP sur le réseau spécifié.
        Exécution bloquante (utilisez scan_async pour non-bloquant).
        
        Args:
            network: Réseau au format CIDR
            progress_callback: Fonction(message, count)
            status_callback: Fonction(message)
            include_ping: Si True, effectue un ping pour chaque appareil
            
        Returns:
            Liste des appareils découverts
        """
        self.scanning = True
        self.results = []
        
        try:
            # Effectue le scan ARP
            self.results = self._perform_arp_scan(
                network, 
                progress_callback=progress_callback,
                status_callback=status_callback
            )
            
            # Optionnel: effectue les pings
            if include_ping and self.results:
                if status_callback:
                    status_callback("Ping des appareils découverts...")
                
                for i, device in enumerate(self.results):
                    ping_time = self._ping_host(device['ip'])
                    device['ping'] = ping_time
                    
                    if progress_callback:
                        ping_str = f"{ping_time:.0f}ms" if ping_time else "timeout"
                        progress_callback(f"Ping {device['ip']}: {ping_str}", i + 1)
            
            if status_callback:
                status_callback("Scan complété")
            
            return self.results
        
        finally:
            self.scanning = False
    
    def scan_async(self, network: str,
                   on_progress: Optional[Callable] = None,
                   on_status: Optional[Callable] = None,
                   on_complete: Optional[Callable] = None,
                   on_error: Optional[Callable] = None,
                   include_ping: bool = False) -> threading.Thread:
        """
        Lance un scan ARP en arrière-plan (dans un thread séparé).
        Parfait pour intégration avec PyQt sans bloquer l'UI.
        
        Args:
            network: Réseau au format CIDR
            on_progress: Callback(message, count)
            on_status: Callback(message)
            on_complete: Callback(results)
            on_error: Callback(error_message)
            include_ping: Si True, effectue un ping
            
        Returns:
            Le thread créé (en cas de besoin de l'arrêter)
        """
        def _scan_thread():
            try:
                results = self.scan(
                    network,
                    progress_callback=on_progress,
                    status_callback=on_status,
                    include_ping=include_ping
                )
                if on_complete:
                    on_complete(results)
            except Exception as e:
                if on_error:
                    on_error(str(e))
        
        self.current_thread = threading.Thread(target=_scan_thread, daemon=True)
        self.current_thread.start()
        return self.current_thread
    
    def stop(self):
        """Arrête le scan en cours (si possible)."""
        self.scanning = False
