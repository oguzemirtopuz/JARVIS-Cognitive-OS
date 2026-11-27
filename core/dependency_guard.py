"""
J.A.R.V.I.S. Dependency Guard & Self-Healing Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bu modül, J.A.R.V.I.S. başlatılırken ortamı ve bağımlılıkları doğrular.
Eğer bir modül eksik veya bozuksa, otomatik olarak (Self-Healing) kurar.
Kullanıcı aylarca projeye girmese veya ortam değişse bile "No module named"
hatalarının önüne geçer.
"""

import sys
import os
import subprocess
import importlib.util
import logging

logger = logging.getLogger("JARVIS.DependencyGuard")

# Doğrulanacak kritik çekirdek bağımlılıklar ve pip paket isimleri
CORE_DEPENDENCIES = [
    ("yaml", "PyYAML>=6.0.2"),
    ("dotenv", "python-dotenv==1.0.1"),
    ("groq", "groq==1.1.2"),
    ("chromadb", "chromadb==1.5.8"),
    ("customtkinter", "customtkinter==5.2.2"),
    ("psutil", "psutil==7.2.2"),
    ("requests", "requests==2.33.1"),
]

def _is_venv_active() -> bool:
    """Mevcut Python sürecinin bir sanal ortamda olup olmadığını kontrol eder."""
    return (
        hasattr(sys, "real_prefix") or
        (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    )

def _switch_to_project_venv(project_root: str) -> bool:
    """
    Eğer proje kökünde .venv varsa ve şu an onun içinde değilsek,
    süreci .venv içindeki Python ile yeniden başlatır.
    """
    venv_pythonw = os.path.join(project_root, ".venv", "Scripts", "pythonw.exe")
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    
    target_python = venv_pythonw if os.path.exists(venv_pythonw) else venv_python
    
    if os.path.exists(target_python) and not _is_venv_active():
        current_exe = os.path.abspath(sys.executable)
        if os.path.abspath(target_python).lower() != current_exe.lower():
            # Script argümanları ile birlikte .venv Python'ına devret
            args = [target_python] + sys.argv
            try:
                subprocess.Popen(args, cwd=project_root)
                sys.exit(0)
            except Exception as e:
                logger.warning(f".venv python başlatılamadı, mevcut python ile devam ediliyor: {e}")
                return False
    return True

def ensure_dependencies(project_root: str, auto_install: bool = True) -> list[str]:
    """
    Kritik modülleri kontrol eder, eksik olanları tespit eder ve gerekirse otomatik kurar.
    Dönen değer: Onarılan/kurulan paketler listesi.
    """
    missing_packages = []
    
    for module_name, pip_spec in CORE_DEPENDENCIES:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            missing_packages.append(pip_spec)
        else:
            # Modül spec bulundu ama içe aktarırken çöküyor mu? (Bozuk dist kontrolü)
            try:
                __import__(module_name)
            except Exception:
                missing_packages.append(pip_spec)

    if missing_packages and auto_install:
        python_exe = sys.executable
        # Eğer pythonw.exe ise terminal gizli çalışacaktır; pip çıktısını yakala
        try:
            cmd = [python_exe, "-m", "pip", "install", "--upgrade"] + missing_packages
            subprocess.check_call(
                cmd,
                cwd=project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            # Kurulan modüllerin import cache'ini temizle
            importlib.invalidate_caches()
        except Exception as e:
            logger.error(f"Eksik paketler otomatik kurulurken hata oluştu: {e}")

    return missing_packages

def ensure_environment(project_root: str | None = None) -> None:
    """
    JARVIS başlatıcıları için tek noktadan ortam ve bağımlılık güvencesi.
    1. .venv yönlendirmesi yapar.
    2. Eksik paket varsa otomatik kurar.
    """
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    _switch_to_project_venv(project_root)
    ensure_dependencies(project_root, auto_install=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixed = ensure_dependencies(root, auto_install=True)
    if fixed:
        print(f"[Self-Healing] Onarılan/kurulan paketler: {fixed}")
    else:
        print("[Self-Healing] Tüm bağımlılıklar eksiksiz ve sağlıklı.")
