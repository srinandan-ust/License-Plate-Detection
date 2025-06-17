# 🚘 Smart License Plate Detection & Logging System

## 📌 Project Overview

A comprehensive IoT-based system for real-time vehicle license plate detection and logging using Raspberry Pi. This project combines computer vision, local and cloud-based logging, and both local and remote user interfaces to enable intelligent vehicle monitoring.

---

## ⚙️ Core Technologies

- **Hardware**: Raspberry Pi 5, camera module
- **Computer Vision**: OpenCV, EasyOCR
- **Frontend**: Flask (HTML5/CSS3), Tkinter GUI
- **Backend**: Python, SQLite, MQTT, ThingsBoard
- **Messaging**: MQTT protocol for IoT data flow
- **Cloud Dashboard**: ThingsBoard for remote visualization

---

## 🚀 Key Features

- 📷 **Real-Time License Plate Detection**  
  Captures and processes live camera feeds to detect license plates using OCR.

- 💾 **Local Logging with SQLite**  
  Logs license plate number, timestamp, confidence, and snapshot locally.

- 🖥️ **Dual Interfaces**  
  - **Web Dashboard (Flask)**: Remote admin control and live video feed  
  - **Local GUI (Tkinter)**: Live monitoring and control on Raspberry Pi

- ☁️ **Cloud Integration**  
  Sends data to ThingsBoard dashboard for centralized cloud monitoring.

- 🧪 **System Logging**  
  Tracks system activity in `app.log` for debugging and analytics.

---

## 🗂️ Folder Structure

```
License-Plate-Detection/
│
├── main_pi.py              # Core detection loop
├── flask_server.py         # Flask-based admin panel
├── db_utils.py             # SQLite DB utilities
├── mqtt_client_pi.py       # Publishes data to MQTT broker
├── ocr_utils.py            # EasyOCR image preprocessing & reading
├── log_utils.py            # Logging setup and management
├── camera_utils.py         # Camera interface functions
├── tb_client.py            # Sends data to ThingsBoard
├── detected_plates.db      # SQLite database file
├── app.log                 # Application logs
├── files.txt               # General file reference (optional)
├── __pycache__/            # Python cache
├── templates/              # HTML templates for Flask UI
│   ├── admin_panel.html    # Main admin dashboard
│   ├── settings.html       # Settings UI
│   ├── logs.html           # Log viewer UI
│   └── login.html          # Authentication UI
├── requirements.txt        # Python dependencies
└── README.md               # This documentation
```

---

## 🔧 Setup Instructions

### ✅ Requirements

- Raspberry Pi 4/5 with Raspbian OS
- Python 3.9+
- Camera connected to Raspberry Pi
- Internet connection (for MQTT/ThingsBoard)

### 🔌 Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-repo/License-Plate-Detection.git
   cd License-Plate-Detection
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Database**
   ```bash
   python db_utils.py  # Optional: create or verify DB structure
   ```

4. **Start System**
   ```bash
   python main_pi.py  # Starts detection and system loop
   ```

5. **Run Flask Dashboard (optional)**
   ```bash
   python flask_server.py
   ```

---

## 🌐 Flask Web Dashboard

- **Live Video Feed**: `http://<RaspberryPi_IP>:5000/video_feed`
- **Admin Panel**: `http://<RaspberryPi_IP>:5000/`

#### Available Features:
- Start/Stop Processing
- View last 50 detections
- Export to CSV
- View logs
- Manage settings
- Clear logs or reset detection data

---

## 🖼️ ThingsBoard Integration

- Configure `tb_client.py` with your ThingsBoard Access Token and MQTT broker details.
- Real-time plate data is published to ThingsBoard for remote visualization and analytics.

---

## 💻 Local GUI (Tkinter)

- Run `main_pi.py` to access the built-in Tkinter dashboard.
- Displays live camera, logs, detection overlay, and system controls.

---

## 📁 Log and Data Management

- Logs saved in `app.log`
- Detections stored in `detected_plates.db` (SQLite)
- Clear or trim database from the Flask UI or via:
  ```bash
  sqlite3 detected_plates.db "DELETE FROM plates WHERE id NOT IN (SELECT id FROM plates ORDER BY timestamp DESC LIMIT 10);"
  ```

---

## 📄 License

This project is for educational/research purposes. Modify and use with credit.

---

## 🤝 Credits

Developed by **PiRates**  🏴‍☠️
