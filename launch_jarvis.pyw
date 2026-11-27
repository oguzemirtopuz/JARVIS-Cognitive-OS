"""
J.A.R.V.I.S. Ghost Mode Launcher
Terminal penceresi GÖSTERMEDEN GUI'yi başlatır.
Bu dosya pythonw.exe ile çalıştırılmalıdır.
Self-Healing & Virtual Environment koruması içerir.
"""
import sys
import os

# Proje kökünü yola ekle
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# [Self-Healing] Ortam ve kritik bağımlılık koruması
try:
    from core.dependency_guard import ensure_environment
    ensure_environment(project_dir)
except Exception as e:
    # Kritik hata durumunda bile sessizce logla ve devam etmeyi dene
    pass

# GUI'yi başlat
from gui.interface import launch_gui
launch_gui()
