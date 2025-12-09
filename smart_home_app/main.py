
"""UI entry point for the Smart Home desktop application using PyQt6."""

import sys
import os
import logging
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from .core.constants import LOG_FILE, ICSEE_CONFIG
from .ui.main_window import SmartHomeApp
import json

# --- Logging Setup ---
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def exception_hook(exctype, value, tb):
    logging.error("Uncaught exception", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook
# ---------------------

class HomeControlApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.socket_name = "home_control_single_instance_socket"
        self.server = QLocalServer(self)
        self.window = None
        self._is_running = False
        
        # Try to connect to existing instance
        socket = QLocalSocket()
        socket.connectToServer(self.socket_name)
        if socket.waitForConnected(500):
            # Another instance exists
            self._is_running = True
            socket.write(b"SHOW")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            # We are the first instance
            self._is_running = False
            # Clean up if previous crash left socket
            self.server.removeServer(self.socket_name)
            self.server.listen(self.socket_name)
            self.server.newConnection.connect(self.on_new_connection)

    def is_running(self):
        return self._is_running

    def on_new_connection(self):
        socket = self.server.nextPendingConnection()
        socket.readyRead.connect(lambda: self.handle_message(socket))

    def handle_message(self, socket):
        msg = socket.readAll().data()
        if msg == b"SHOW":
            self.activate_window()

    def activate_window(self):
        if self.window:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()

    def event(self, event):
        # Handle clicking the Dock icon on macOS
        if event.type() == QEvent.Type.ApplicationActivate:
            self.activate_window()
        return super().event(event)

def run_app():
    app = HomeControlApplication(sys.argv)
    
    if app.is_running():
        print("Another instance is already running. Focusing existing window.")
        sys.exit(0)
    
    # Load fonts
    QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "fonts/SF-Pro-Display-Regular.otf"))
    QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "fonts/SF-Pro-Display-Bold.otf"))
    QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "fonts/SF-Pro-Text-Regular.otf"))
    
    
    # Start go2rtc bridge
    import subprocess
    import signal
    import tempfile
    
    go2rtc_process = None
    
    # Generate go2rtc.yaml to temp location
    yaml_path = os.path.join(tempfile.gettempdir(), "home_control_go2rtc.yaml")
    
    # Bundle-aware path resolution
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        project_root = sys._MEIPASS
        # Fix: App bundles have restricted PATH. Add common locations for ffmpeg.
        if os.name != 'nt':
             paths = ["/usr/local/bin", "/opt/homebrew/bin", "/opt/local/bin", "/usr/bin", "/bin"]
             current_path = os.environ.get("PATH", "")
             for p in paths:
                 if p not in current_path and os.path.exists(p):
                     os.environ["PATH"] += os.pathsep + p
    else:
        # Running from source
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cross-platform binary name
    bin_name = "go2rtc.exe" if os.name == 'nt' else "go2rtc"
    go2rtc_path = os.path.join(project_root, bin_name)
    
    # Generate go2rtc.yaml to temp location
    yaml_path = os.path.join(tempfile.gettempdir(), "home_control_go2rtc.yaml")
    
    if os.path.exists(ICSEE_CONFIG):
        try:
            streams = {}
            with open(ICSEE_CONFIG, 'r') as f:
                data = json.load(f)
                for i, cam in enumerate(data.get("cameras", [])):
                    if cam.get("protocol") == "xmeye":
                        user = cam.get("user", "admin")
                        pwd = cam.get("pass", "")
                        ip = cam.get("ip", "")
                        if ip:
                            # dvrip scheme for XMeye cameras
                            # channel=0 default
                            streams[f"cam_{i}_raw"] = f"dvrip://{user}:{pwd}@{ip}"
                            streams[f"cam_{i}"] = f"ffmpeg:rtsp://127.0.0.1:8554/cam_{i}_raw#video=h264"
            
            if streams:
                with open(yaml_path, "w") as f:
                    f.write("api:\n  listen: \":1984\"\n")
                    f.write("streams:\n")
                    for k, v in streams.items():
                        f.write(f"  {k}: {v}\n")
                logging.info(f"Generated go2rtc config at {yaml_path}")
        except Exception as e:
            logging.error(f"Failed to generate go2rtc config: {e}")

    # Start go2rtc with the generated config
    # Ensure no zombies
    try:
        if os.name == 'nt':
             subprocess.run(["taskkill", "/F", "/IM", "go2rtc.exe"], stderr=subprocess.DEVNULL)
        else:
             subprocess.run(["pkill", "go2rtc"], stderr=subprocess.DEVNULL)
    except: pass
    
    # Cleanup old local file if exists to avoid confusion
    if os.path.exists(os.path.join(project_root, "go2rtc.yaml")):
        try: os.remove(os.path.join(project_root, "go2rtc.yaml"))
        except: pass

    if os.path.exists(go2rtc_path):
        try:
            # FIX: PyInstaller 'onefile' extracts to tmp without execute permissions on macOS/Linux
            if os.name != 'nt':
                os.chmod(go2rtc_path, 0o755)

            logging.info(f"Starting go2rtc bridge from {go2rtc_path}...")
            
            # Redirect go2rtc output to the main log file (or separate) so we can see it
            # sys.stdout/stderr are None in --noconsole mode
            
            # We use the same log file handle? Or just pipe to subprocess.PIPE and log lines?
            # Piping and logging lines in a thread is best but complex.
            # Simpler: Redirect to a dedicated log file for go2rtc
            rtc_log_path = os.path.join(os.path.dirname(LOG_FILE), "go2rtc.log")
            
            rtc_log = open(rtc_log_path, "w")
            go2rtc_process = subprocess.Popen(
                [go2rtc_path, "-c", yaml_path], 
                cwd=project_root, 
                stdout=rtc_log, 
                stderr=subprocess.STDOUT
            )
            logging.info(f"go2rtc started. PID: {go2rtc_process.pid}. Logs at {rtc_log_path}")
            
        except Exception as e:
            logging.error(f"Failed to start go2rtc: {e}")
    else:
        logging.error(f"go2rtc binary NOT found at {go2rtc_path}")

    window = SmartHomeApp()
    app.window = window
    window.show()
    
    exit_code = app.exec()
    
    # Cleanup
    if go2rtc_process:
        logging.info("Stopping go2rtc bridge...")
        go2rtc_process.terminate()
        try:
            go2rtc_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            go2rtc_process.kill()
        
        # Close log file
        try:
            rtc_log.close()
        except: pass
            
    sys.exit(exit_code)
