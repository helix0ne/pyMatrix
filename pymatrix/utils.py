"""
PyMatrix Shared Utilities
Gemeinsame Funktionen fuer pymatrix und model_manager Module.
Vermeidet Code-Duplikation bei Formatierung, Symlinks, Konstanten.
"""

import os
import subprocess
import sys
from pathlib import Path

# ── Konstanten ────────────────────────────────────────────────
CHUNK_SIZE = 65536            # 64 KB — Standard-Download-Chunk
CHUNK_SIZE_LARGE = 262144     # 256 KB — Grosse Downloads
BYTES_PER_MB = 1_048_576      # 1 MB in Bytes
FILE_ATTR_REPARSE = 0x400     # Windows FILE_ATTRIBUTE_REPARSE_POINT
TIMEOUT_SHORT = 10            # Sekunden — schnelle Ops (git rev-parse)
TIMEOUT_MEDIUM = 120          # Sekunden — Downloads, API-Calls
TIMEOUT_LONG = 300            # Sekunden — pip install, grosse Downloads
TIMEOUT_INSTALL = 600         # Sekunden — Paket-Installationen


# ── Formatierung ──────────────────────────────────────────────

def fmt_size(bytes_val: int | float) -> str:
    """Formatiert Bytes als menschenlesbare Groesse (z.B. '4.2 GB')."""
    if bytes_val <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def fmt_speed(bytes_per_sec: float) -> str:
    """Formatiert Download-Geschwindigkeit (z.B. '12.5 MB/s')."""
    return f"{fmt_size(bytes_per_sec)}/s"


# ── Symlink / Junction ───────────────────────────────────────

def is_windows() -> bool:
    """Prueft ob Windows-Plattform."""
    return sys.platform == "win32"


def is_link(path: Path) -> bool:
    """
    Prueft ob ein Pfad ein Symlink oder Windows Junction ist.
    Funktioniert auf Windows und Unix.
    """
    if path.is_symlink():
        return True
    if is_windows() and path.exists():
        try:
            # Pruefe REPARSE_POINT via stat (Junctions)
            st = path.stat()
            if hasattr(st, "st_reparse_tag"):
                return st.st_reparse_tag != 0
            # Fallback: ctypes
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            return bool(attrs & FILE_ATTR_REPARSE)
        except (OSError, AttributeError, ValueError):
            pass
    return False


def create_link(source: Path, link: Path) -> str:
    """
    Erstellt Junction (Windows) oder Symlink (Unix).
    source: Ziel-Ordner (wohin der Link zeigt)
    link:   Link-Pfad (der erstellt wird)
    Gibt Fehler-String zurueck oder '' bei Erfolg.
    """
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        if is_windows():
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(source)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                # Fallback: os.symlink (erfordert Developer Mode / Admin)
                os.symlink(str(source), str(link))
        else:
            link.symlink_to(source)
    except OSError as e:
        return str(e)
    return ""


def remove_link(link: Path) -> bool:
    """
    Entfernt einen Symlink oder Windows Junction.
    Gibt True bei Erfolg, False bei Fehler zurueck.
    """
    try:
        if is_windows():
            result = subprocess.run(
                ["cmd", "/c", "rmdir", str(link)],
                capture_output=True
            )
            return result.returncode == 0
        else:
            link.unlink()
            return True
    except OSError:
        return False
