#!/usr/bin/env python3
"""
WiFi Manager - Message Listener
Programme léger à exécuter sur les appareils qui doivent recevoir des messages.
"""

import socket
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import sys

class MessageListener:
    """Écoute les messages UDP et affiche des popups."""
    
    def __init__(self, port=9999):
        """
        Initialise le listener.
        
        Args:
            port: Port UDP à écouter (par défaut 9999)
        """
        self.port = port
        self.running = False
        self.sock = None
        self.listener_thread = None
        
    def start(self):
        """Démarre l'écoute des messages."""
        if self.running:
            print("Listener déjà en cours d'exécution")
            return
        
        try:
            # Crée le socket UDP
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', self.port))
            self.sock.settimeout(1.0)  # Timeout pour vérifier self.running
            
            self.running = True
            
            # Démarre le thread d'écoute
            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listener_thread.start()
            
            print(f"✓ Listener démarré sur le port {self.port}")
            print(f"✓ En attente de messages...")
            
        except Exception as e:
            print(f"✗ Erreur lors du démarrage: {e}")
            self.running = False
    
    def stop(self):
        """Arrête l'écoute."""
        self.running = False
        if self.sock:
            self.sock.close()
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
        print("Listener arrêté")
    
    def _listen_loop(self):
        """Boucle d'écoute principale."""
        while self.running:
            try:
                # Attend un message
                data, addr = self.sock.recvfrom(4096)
                
                # Décode le message
                message = data.decode('utf-8', errors='ignore')
                
                # Log
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Message reçu de {addr[0]}:{addr[1]}")
                print(f"Message: {message}")
                print("-" * 50)
                
                # Affiche un popup
                self._show_popup(message, addr[0])
                
            except socket.timeout:
                # Timeout normal, continue
                continue
            except Exception as e:
                if self.running:
                    print(f"Erreur de réception: {e}")
    
    def _show_popup(self, message, sender_ip):
        """
        Affiche un popup avec le message.
        
        Args:
            message: Message à afficher
            sender_ip: IP de l'expéditeur
        """
        try:
            # Crée une fenêtre Tkinter temporaire
            root = tk.Tk()
            root.withdraw()  # Cache la fenêtre principale
            
            # Affiche le message
            messagebox.showinfo(
                "Network Message",
                f"Message de {sender_ip}:\n\n{message}"
            )
            
            root.destroy()
            
        except Exception as e:
            print(f"Erreur d'affichage popup: {e}")


class ListenerGUI:
    """Interface graphique pour le listener."""
    
    def __init__(self):
        """Initialise l'interface."""
        self.root = tk.Tk()
        self.root.title("WiFi Manager - Message Listener")
        self.root.geometry("400x300")
        
        self.listener = None
        self.port = tk.IntVar(value=9999)
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crée les widgets de l'interface."""
        # Titre
        title = tk.Label(
            self.root,
            text="WiFi Manager Message Listener",
            font=("Arial", 14, "bold")
        )
        title.pack(pady=10)
        
        # Port
        port_frame = tk.Frame(self.root)
        port_frame.pack(pady=5)
        
        tk.Label(port_frame, text="Port UDP:").pack(side=tk.LEFT, padx=5)
        port_entry = tk.Entry(port_frame, textvariable=self.port, width=10)
        port_entry.pack(side=tk.LEFT)
        
        # Statut
        self.status_label = tk.Label(
            self.root,
            text="● Arrêté",
            fg="red",
            font=("Arial", 12)
        )
        self.status_label.pack(pady=10)
        
        # Boutons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            button_frame,
            text="▶ Démarrer",
            command=self._start_listener,
            bg="#4CAF50",
            fg="white",
            width=15,
            font=("Arial", 10, "bold")
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            button_frame,
            text="■ Arrêter",
            command=self._stop_listener,
            bg="#f44336",
            fg="white",
            width=15,
            font=("Arial", 10, "bold"),
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Log
        log_label = tk.Label(self.root, text="Derniers messages:")
        log_label.pack(pady=5)
        
        self.log_text = tk.Text(self.root, height=8, width=45, bg="#f0f0f0")
        self.log_text.pack(pady=5)
        
        # Instructions
        info = tk.Label(
            self.root,
            text="Ce programme écoute les messages du réseau\net affiche des popups.",
            font=("Arial", 8),
            fg="gray"
        )
        info.pack(pady=5)
    
    def _start_listener(self):
        """Démarre le listener."""
        try:
            port = self.port.get()
            self.listener = MessageListener(port)
            self.listener.start()
            
            self.status_label.config(text=f"● En écoute sur le port {port}", fg="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            self._log(f"Listener démarré sur le port {port}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de démarrer:\n{e}")
    
    def _stop_listener(self):
        """Arrête le listener."""
        if self.listener:
            self.listener.stop()
            self.listener = None
        
        self.status_label.config(text="● Arrêté", fg="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self._log("Listener arrêté")
    
    def _log(self, message):
        """Ajoute un message au log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def run(self):
        """Lance l'interface."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self):
        """Gère la fermeture de la fenêtre."""
        if self.listener:
            self.listener.stop()
        self.root.destroy()


if __name__ == "__main__":
    print("WiFi Manager - Message Listener")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Mode console
        port = 9999
        if len(sys.argv) > 2:
            port = int(sys.argv[2])
        
        listener = MessageListener(port)
        listener.start()
        
        try:
            print("\nAppuyez sur Ctrl+C pour arrêter...")
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nArrêt...")
            listener.stop()
    else:
        # Mode GUI
        app = ListenerGUI()
        app.run()
