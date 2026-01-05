"""
Module to resolve device names using NetBIOS (Windows) and mDNS (Bonjour).
"""
import socket
import subprocess
import platform
from typing import Optional

class DeviceNameResolver:
    @staticmethod
    def netbios_name(ip: str, timeout: int = 2) -> Optional[str]:
        """
        Try to resolve NetBIOS name (Windows devices).
        Returns the name or None.
        """
        try:
            if platform.system().lower() == 'windows':
                # Use nbtstat command
                result = subprocess.run([
                    'nbtstat', '-A', ip
                ], capture_output=True, timeout=timeout)
                output = result.stdout.decode(errors='ignore')
                for line in output.splitlines():
                    if '<00>' in line and 'UNIQUE' in line:
                        name = line.split()[0].strip()
                        return name
            else:
                # On Linux, use nmblookup if available
                result = subprocess.run([
                    'nmblookup', '-A', ip
                ], capture_output=True, timeout=timeout)
                output = result.stdout.decode(errors='ignore')
                for line in output.splitlines():
                    if '<00>' in line:
                        name = line.split()[0].strip()
                        return name
        except Exception:
            return None
        return None

    @staticmethod
    def mdns_name(ip: str, timeout: int = 2) -> Optional[str]:
        """
        Try to resolve mDNS/Bonjour name (Apple devices, some IoT).
        Returns the name or None.
        """
        try:
            # Try to connect to port 5353 (mDNS)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(b'', (ip, 5353))
            # Not a real mDNS query, but may trigger a response
            sock.close()
        except Exception:
            pass
        # Real mDNS queries require a library like zeroconf (not included)
        return None

    @staticmethod
    def resolve(ip: str) -> Optional[str]:
        """
        Try all methods to resolve device name.
        """
        name = DeviceNameResolver.netbios_name(ip)
        if name:
            return name
        name = DeviceNameResolver.mdns_name(ip)
        if name:
            return name
        return None
