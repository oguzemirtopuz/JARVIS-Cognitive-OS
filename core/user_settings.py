import os
import json
import logging
import winreg

logger = logging.getLogger("JARVIS.UserSettings")

SETTINGS_FILE = "settings.json"

class UserSettings:
    """Singleton for managing user settings across sessions."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSettings, cls).__new__(cls)
            cls._instance._init_settings()
        return cls._instance

    def _init_settings(self):
        self.default_settings = {
            "screen_analysis_interval": 900,  # in seconds (15 minutes)
            "auto_start": False,
            "language": "tr"
        }
        self.settings = self.default_settings.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.settings[k] = v
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        else:
            self.save()

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    # ── Auto Start Logic ──
    def update_auto_start(self, enabled: bool):
        self.set("auto_start", enabled)
        self._set_windows_run_key(enabled)

    def _set_windows_run_key(self, enable: bool):
        """Adds or removes the J.A.R.V.I.S. startup entry in the Windows Registry."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "JARVIS_OS"
        # Since we might be running via main.py, we figure out the launch command
        # For a robust solution, we use pythonw.exe and absolute path to main.py
        import sys
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                # Path to the python executable and the main script
                python_exe = sys.executable
                if "python.exe" in python_exe:
                    python_exe = python_exe.replace("python.exe", "pythonw.exe") # run in background if possible
                    
                main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                command = f'"{python_exe}" "{main_script}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
                logger.info("[Settings] Added Auto-Start registry key.")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info("[Settings] Removed Auto-Start registry key.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"[Settings] Failed to modify registry for auto-start: {e}")

