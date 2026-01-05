# WiFi Manager Pro 🌐

**Enterprise Network Management System** - A comprehensive Python desktop application for network scanning, monitoring, and device control.

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/zahdineamine2003/Wifi-manager-ARP-)

---

## 📸 Screenshots

### Main Interface
![Main Interface](screenshots/01_main_interface.png)
*Professional dark-themed interface with network configuration panel*

### Network Scanning
![Scanning in Progress](screenshots/02_scanning.png)
*Real-time ARP scanning with progress tracking*

### Detected Devices
![Devices Detected](screenshots/03_devices_detected.png)
*Comprehensive device table with IP, MAC, vendor, and network metrics*

### Live Monitoring
![Monitoring Graphs](screenshots/04_monitoring_graphs.png)
*Dual-axis graphs showing real-time network statistics*

### Smart TV Remote Control
![TV Remote Control](screenshots/05_tv_remote.png)
*Complete TV remote control interface supporting 10+ brands*

### Device Management
![Kick Operation](screenshots/06_kick_dialog.png)
*Advanced device disconnection with configurable duration*

---

## 🎥 Demo Video

### Device Kick Operation Demo
Watch the full demonstration of the device disconnection feature:

https://github.com/zahdineamine2003/Wifi-manager-ARP-/assets/demo/kick_operation_demo.mp4

*30-second demo showing how to temporarily disconnect a device from the network*

> **Note:** Upload your video to the `demo/` folder or host it on YouTube and update the link above.

---

## ✨ Key Features

### 🔍 Network Discovery
- **ARP Scanning**: Fast network-wide device discovery using Scapy
- **CIDR Configuration**: Flexible network range specification
- **Vendor Identification**: Automatic manufacturer lookup via IEEE OUI database (25,000+ entries)
- **Smart Detection**: Multi-criteria TV and mobile device recognition
- **Ping Integration**: Optional latency measurement for each device

### 📊 Real-Time Monitoring
- **Live Graphs**: Dual-axis charts tracking device counts and signal strength
- **Network Analytics**: Bandwidth aggregation and uptime calculation
- **5-Minute Window**: Rolling data display with 5-second updates
- **Color-Coded Metrics**: Intuitive visualization with professional dark theme

### 🎮 Device Management
- **Individual Kick**: Disconnect specific devices via ARP spoofing
- **Mass Kick**: Remove all devices except your own
- **Configurable Duration**: Set temporary or indefinite disconnection
- **Safety Features**: Automatic self-exclusion and gateway validation

### 📺 Smart TV Control
- **Auto-Detection**: Identifies TVs from 10+ brands (Samsung, LG, Sony, Philips, etc.)
- **Wake-on-LAN**: Power on TVs remotely
- **Complete Remote**: Volume, channels, navigation, and input control
- **App Launching**: Direct access to Netflix, YouTube, and more

### 📨 Multi-Protocol Messaging
- **Web Hijacking**: Display messages in target's browser automatically
- **UDP/TCP/Broadcast**: Multiple delivery methods for maximum compatibility
- **Windows Notifications**: System-level popups (when configured)
- **HTTP Integration**: Webhook and REST API support

### 💾 Data Export & Logging
- **CSV Export**: Timestamped reports with complete device information
- **Real-Time Logs**: Live event tracking in dedicated panel
- **UTF-8 Support**: International character compatibility

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.7+** installed
- **Administrator/Root privileges** (required for network access)
- **Windows/Linux/macOS** compatible

### Installation (Automated)

#### Windows
```batch
# Right-click and "Run as Administrator"
install_and_run.bat
```

#### Linux/macOS
```bash
chmod +x install_and_run.sh
sudo ./install_and_run.sh
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/zahdineamine2003/Wifi-manager-ARP-.git
cd Wifi-manager-ARP-

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
# Windows (as Administrator):
python main.py
# Linux/macOS:
sudo python main.py
```

---

## 💻 Usage

### Basic Workflow

1. **Launch as Administrator**
   ```
   Right-click main.py → Run as Administrator
   ```

2. **Configure Network**
   - CIDR auto-detected (e.g., 192.168.1.0/24)
   - Adjust timeout (recommended: 8-10 seconds for TVs/mobiles)
   - Enable "Ping mode" for latency measurement

3. **Scan Network**
   - Click "🔍 Scan" button
   - Wait for scan to complete (1-2 minutes depending on network size)
   - Devices appear in table with full details

4. **Manage Devices**
   - **Kick Device**: Right-click → Select duration → Confirm
   - **Send Message**: Click "📨 Message" → Choose protocol → Send
   - **Control TV**: Click "📺 TV Remote" → Select your TV

5. **Monitor Network**
   - Switch to "📈 Monitoring" tab
   - View live graphs updating every 5 seconds
   - Track device trends over 5-minute window

6. **Export Results**
   - Click "💾 Export" button
   - Choose save location
   - File saved as `scan_YYYYMMDD_HHMMSS.csv`

---

## 🛠️ Technology Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.7+ |
| **GUI Framework** | PyQt5 |
| **Network Library** | Scapy |
| **Visualization** | Matplotlib |
| **Protocols** | ARP, ICMP, TCP/UDP, HTTP, Wake-on-LAN |
| **Architecture** | Multi-threaded, Event-driven |

---

## 📋 Project Structure

```
Wifi-manager-ARP-/
├── main.py                          # Application entry point
├── scanner/                         # Network scanning modules
│   ├── __init__.py
│   ├── arp_scanner.py              # ARP scanning engine
│   ├── name_resolver.py            # Device name resolution
│   ├── tv_controller.py            # Smart TV control logic
│   └── utils.py                    # Utilities (OUI, CIDR, CSV)
├── ui/                             # User interface
│   ├── __init__.py
│   └── main_window.py              # Main PyQt5 window
├── screenshots/                     # Application screenshots
├── demo/                           # Demo videos
├── requirements.txt                 # Python dependencies
├── install_and_run.bat             # Windows installer
├── install_and_run.sh              # Linux/macOS installer
├── test_units.py                   # Unit tests
└── README.md                       # This file
```

---

## 🔒 Security Considerations

### ⚠️ Important Warnings

This tool includes **powerful network manipulation features**:

- **ARP Spoofing**: Can disrupt network connectivity
- **Device Kicking**: May disconnect critical services
- **Web Hijacking**: Intercepts HTTP traffic temporarily

### Ethical Use Guidelines

✅ **DO:**
- Use only on networks you own or have explicit permission to test
- Inform users before performing network tests
- Keep administrator access restricted
- Use for educational and legitimate IT purposes

❌ **DON'T:**
- Use on public or unauthorized networks
- Disrupt critical infrastructure
- Violate privacy or computer fraud laws
- Deploy without proper authorization

### Legal Notice

Network scanning and ARP spoofing may be **illegal** in some jurisdictions without proper authorization. Always:
- Obtain written permission before testing
- Comply with local computer fraud and abuse laws
- Use responsibly and ethically

---

## 🐛 Troubleshooting

### Common Issues

#### No Devices Detected
**Problem:** Scan completes but shows 0 devices

**Solutions:**
1. Run as **Administrator/Root**
2. Increase timeout to **8-10 seconds**
3. Enable **Ping mode**
4. Wake up devices (turn on TVs, unlock phones)
5. Perform **2-3 scans** (first scan wakes devices)
6. Check CIDR range matches your network

#### TVs Not Detected
**Problem:** Smart TVs don't appear in scan

**Solutions:**
1. Turn TV on completely (not standby)
2. Open Netflix/YouTube on TV
3. Increase timeout to 8+ seconds
4. Manually select device by IP (.254, .100, etc.)
5. Disable "AP Isolation" in router settings

#### Permission Errors
**Problem:** "Access Denied" or "Permission Error"

**Solutions:**
1. **Windows**: Right-click → Run as Administrator
2. **Linux/macOS**: Use `sudo python main.py`
3. Install **Npcap** on Windows (https://npcap.com/)
4. Check firewall settings

#### Kick Doesn't Work
**Problem:** Device stays connected

**Solutions:**
1. Verify admin privileges
2. Check gateway detection succeeded
3. Increase kick duration
4. Ensure no ARP protection on network
5. Test with a non-critical device first

---

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get started in 30 seconds
- **[USAGE.md](USAGE.md)** - Detailed usage guide with examples
- **[COMPLETE_PROJECT_DESCRIPTION.txt](COMPLETE_PROJECT_DESCRIPTION.txt)** - Full technical documentation
- **[LINKEDIN_DESCRIPTION.txt](LINKEDIN_DESCRIPTION.txt)** - Professional project summary

---

## 🧪 Testing

Run unit tests to verify installation:

```bash
python test_units.py
```

Tests include:
- CIDR validation
- IP address validation
- OUI database functionality
- CSV export
- Configuration management

---

## 📦 Building Standalone Executable

Create a standalone .exe (Windows):

```bash
pip install pyinstaller
pyinstaller WIFI_Manager.spec
```

Executable will be in `dist/` folder.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Areas for Improvement
- Additional TV brand support
- Enhanced device type detection
- Network topology visualization
- Historical data persistence
- Multi-language support

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Zahdine Amine**
- GitHub: [@zahdineamine2003](https://github.com/zahdineamine2003)
- LinkedIn: [Add your LinkedIn profile]

---

## 🙏 Acknowledgments

- **Scapy** - Powerful packet manipulation library
- **PyQt5** - Excellent GUI framework
- **IEEE** - OUI database for vendor identification
- Open source community for inspiration and tools

---

## 📊 Project Stats

![Code Size](https://img.shields.io/github/languages/code-size/zahdineamine2003/Wifi-manager-ARP-)
![Last Commit](https://img.shields.io/github/last-commit/zahdineamine2003/Wifi-manager-ARP-)
![Stars](https://img.shields.io/github/stars/zahdineamine2003/Wifi-manager-ARP-?style=social)

---

## 🔗 Related Projects

- [Scapy](https://scapy.net/) - Packet manipulation program
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Python GUI framework
- [Npcap](https://npcap.com/) - Packet capture library for Windows

---

<div align="center">

**⭐ Star this repository if you find it useful!**

Made with ❤️ by Zahdine Amine

[Report Bug](https://github.com/zahdineamine2003/Wifi-manager-ARP-/issues) · [Request Feature](https://github.com/zahdineamine2003/Wifi-manager-ARP-/issues)

</div>
