"""
PyMatrix — Python-basierter StabilityMatrix Fork
Laedt bestehende SM-Installation, verwaltet WebUI-Pakete,
integriert SD Model Manager v2.0

Aufruf: python app.py
"""

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# ── Eigene Module ─────────────────────────────────────────
_BASE = Path(__file__).parent
sys.path.insert(0, str(_BASE / ".." / "model_manager"))  # Model Manager Module

from core import PyMatrixConfig, PackageLauncher, Package, KNOWN_PACKAGES, DEFAULT_SM_ROOT

try:
    from downloader import (CivitAIClient, HuggingFaceClient, DownloadManager,
                            DownloadTask, detect_source, fmt_size, fmt_speed)
    HAS_DOWNLOADER = True
except ImportError:
    HAS_DOWNLOADER = False

try:
    from scanner import scan_folder_sizes, find_duplicates, find_orphans, fmt_size as scan_fmt_size
    HAS_SCANNER = True
except ImportError:
    HAS_SCANNER = False

try:
    import model_manager_bridge as mmb
    HAS_MM = True
except ImportError:
    # Model Manager Kernfunktionen direkt importieren
    try:
        sys.path.insert(0, str(_BASE / ".." / "model_manager"))
        from app import (
            load_master_types, load_profiles, master_folder, apply_profile,
            create_link, is_link, C as MM_C, master_types, profiles,
        )
        HAS_MM = True
    except Exception:
        HAS_MM = False

try:
    from packages_catalog import PACKAGE_CATALOG, PackageDef, get_webui_packages, get_training_packages
    from installer import PackageInstaller, SharedFolderManager
    HAS_INSTALLER = True
except ImportError:
    HAS_INSTALLER = False

try:
    from extensions import (ExtensionManager, ExtensionDef, InstalledExtension,
                             COMFYUI_NODES_CATALOG, A1111_EXTENSIONS_CATALOG)
    HAS_EXT = True
except ImportError:
    HAS_EXT = False

# ─────────────────────────── Theme ───────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

C = {
    "bg":       "#1e1e2e",
    "surface":  "#27273a",
    "card":     "#313244",
    "border":   "#45475a",
    "text":     "#cdd6f4",
    "subtext":  "#7f849c",
    "green":    "#a6e3a1",
    "yellow":   "#f9e2af",
    "red":      "#f38ba8",
    "blue":     "#89b4fa",
    "sky":      "#89dceb",
    "mauve":    "#cba6f7",
    "peach":    "#fab387",
    "teal":     "#94e2d5",
    "lavender": "#b4befe",
    "pink":     "#f5c2e7",
    "rosewater":"#f5e0dc",
}

VERSION = "2.0.0"
APP_NAME = "PyMatrix"

# ─────────────────────────── Hilfs-Widgets ───────────────────

def badge(parent, text: str, color: str, **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, width=10,
                        fg_color=color, text_color=C["bg"],
                        corner_radius=4, font=("Segoe UI", 10, "bold"), **kw)


def section_label(parent, text: str, **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text,
                        font=("Segoe UI", 11, "bold"),
                        text_color=C["subtext"], **kw)


def hline(parent) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, height=1, fg_color=C["border"])


def fmt_commit(sha: str) -> str:
    return sha[:8] if sha else "?"


# ─────────────────────────── Haupt-App ───────────────────────

class PyMatrixApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Konfiguration laden
        self.cfg = PyMatrixConfig(sm_root=DEFAULT_SM_ROOT)
        self.cfg.load()
        self.launcher = PackageLauncher(self.cfg)
        self.launcher.on_output = self._on_pkg_output

        if HAS_DOWNLOADER:
            self._dl_mgr = DownloadManager(max_concurrent=2)
            self._dl_mgr.on_complete = self._on_dl_complete
        else:
            self._dl_mgr = None

        # Installer & Extension Manager
        if HAS_INSTALLER:
            self._installer = PackageInstaller(self.cfg.sm_root)
            self._sf_manager = SharedFolderManager(
                self.cfg.sm_root, self.cfg.models_root)
        else:
            self._installer = None
            self._sf_manager = None

        if HAS_EXT:
            self._ext_manager = ExtensionManager(self.cfg.packages_root)
        else:
            self._ext_manager = None

        # Model Manager
        if HAS_MM:
            try:
                load_master_types()
                load_profiles()
            except Exception:
                pass

        # UI
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1400x900")
        self.configure(fg_color=C["bg"])
        self.minsize(1000, 680)

        self._active_idx = -1
        self._active_page = None
        self._pkg_log_buffers: dict[str, list[str]] = {}
        self._detected_urls: dict[str, str] = {}   # pkg_id → zuletzt erkannte URL
        self._selected_pkg: Package | None = None

        self._build_ui()

        # Auto-Refresh Timer
        self._status_timer()

        # Beim Schliessen alle Prozesse stoppen
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI-Aufbau ──────────────────────────────────────────

    def _build_ui(self):
        # Status Bar
        self.sb = ctk.CTkFrame(self, height=28, fg_color=C["surface"], corner_radius=0)
        self.sb.pack(side="bottom", fill="x")
        self.sb.pack_propagate(False)
        self._sb_left = ctk.CTkLabel(self.sb, text="", font=("Segoe UI", 10),
                                      text_color=C["subtext"], anchor="w")
        self._sb_left.pack(side="left", padx=12)
        self._sb_right = ctk.CTkLabel(self.sb, text=f"{APP_NAME} v{VERSION}",
                                       font=("Segoe UI", 10), text_color=C["subtext"],
                                       anchor="e")
        self._sb_right.pack(side="right", padx=12)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=230, fg_color=C["surface"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(20, 4))
        ctk.CTkLabel(logo, text="Py", font=("Segoe UI", 26, "bold"),
                     text_color=C["mauve"]).pack(side="left")
        ctk.CTkLabel(logo, text="Matrix", font=("Segoe UI", 26, "bold"),
                     text_color=C["lavender"]).pack(side="left")
        ctk.CTkLabel(self.sidebar, text=f"v{VERSION}  \u2022  fork of StabilityMatrix",
                     font=("Segoe UI", 9), text_color=C["subtext"]).pack(
            anchor="w", padx=16, pady=(0, 16))
        hline(self.sidebar).pack(fill="x", padx=12, pady=(0, 8))

        # Navigation
        self._nav_btns: list[ctk.CTkButton] = []
        self._nav_items_cfg = [
            ("\u25A0  Startseite",        0),
            ("\u25B6  Pakete / Launcher",  1),
            ("\u2B07  Model Manager",     2),
            ("\u25BC  Downloader",        3),
            ("\u25C6  Scanner",           4),
            ("\u2795  Paket Browser",     7),
            ("\u26D1  Extensions",        8),
            ("\u2699  Einstellungen",     5),
        ]
        for lbl, idx in self._nav_items_cfg:
            btn = ctk.CTkButton(
                self.sidebar, text=lbl, anchor="w",
                fg_color="transparent", hover_color=C["card"],
                text_color=C["text"], font=("Segoe UI", 13),
                corner_radius=8, height=42,
                command=lambda i=idx: self._navigate(i),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_btns.append(btn)

        hline(self.sidebar).pack(fill="x", padx=12, pady=8)

        # Laufende Pakete (Live-Anzeige)
        section_label(self.sidebar, "LAUFENDE PAKETE").pack(anchor="w", padx=12, pady=(4, 4))
        self._running_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self._running_frame.pack(fill="x", padx=8)

        # Untere Buttons
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=8, pady=8)
        ctk.CTkButton(bottom, text="\u21BB  Neu laden", anchor="w",
                      fg_color="transparent", hover_color=C["card"],
                      text_color=C["subtext"], font=("Segoe UI", 12),
                      corner_radius=6, height=34,
                      command=self._reload).pack(fill="x", pady=1)
        ctk.CTkButton(bottom, text="\u2630  Log", anchor="w",
                      fg_color="transparent", hover_color=C["card"],
                      text_color=C["subtext"], font=("Segoe UI", 12),
                      corner_radius=6, height=34,
                      command=lambda: self._navigate(6)).pack(fill="x", pady=1)

        # Hauptbereich
        self.main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        # Toast
        self._toast = ctk.CTkLabel(self.main, text="",
                                    font=("Segoe UI", 11, "bold"),
                                    fg_color=C["green"], text_color=C["bg"],
                                    corner_radius=8)

        # Seiten (Index entspricht nav_idx)
        self._pages = {
            0: self._build_home(),
            1: self._build_packages(),
            2: self._build_model_mgr(),
            3: self._build_downloader(),
            4: self._build_scanner(),
            5: self._build_settings(),
            6: self._build_log(),
            7: self._build_pkg_browser(),
            8: self._build_ext_manager(),
        }
        self._navigate(0)

    def _navigate(self, idx: int):
        if self._active_page:
            self._active_page.pack_forget()
        page = self._pages[idx]
        page.pack(fill="both", expand=True, padx=20, pady=16)
        self._active_page = page
        self._active_idx = idx

        # Nav-Buttons highlighten
        running_count = len(self.launcher.get_running_ids())
        for btn_pos, (lbl, nav_idx) in enumerate(self._nav_items_cfg):
            btn = self._nav_btns[btn_pos]
            # Pakete-Button: Running-Count Badge
            if nav_idx == 1 and running_count > 0:
                display_lbl = f"\u25B6  Pakete / Launcher  [{running_count}]"
            else:
                display_lbl = lbl
            btn.configure(
                text=display_lbl,
                fg_color=C["card"] if nav_idx == idx else "transparent",
                text_color=C["mauve"] if nav_idx == idx else C["text"],
            )

        refresh = {
            0: self._refresh_home,
            1: self._refresh_packages,
            7: self._refresh_pkg_browser,
        }
        if idx in refresh:
            refresh[idx]()

    def _toast_show(self, msg: str, color: str = None, ms: int = 3000):
        self._toast.configure(text=f"  {msg}  ", fg_color=color or C["green"],
                               text_color=C["bg"])
        self._toast.place(relx=1.0, rely=0.0, anchor="ne", x=-12, y=12)
        self.after(ms, self._toast.place_forget)

    def _reload(self):
        self.cfg.load()
        if HAS_MM:
            try:
                load_master_types()
                load_profiles()
            except Exception:
                pass
        self.refresh_all()

    def refresh_all(self):
        if self._active_idx == 0:
            self._refresh_home()
        elif self._active_idx == 1:
            self._refresh_packages()

    # ─── Startseite ────────────────────────────────────────

    def _build_home(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        # Header
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(hdr, text="PyMatrix", font=("Segoe UI", 32, "bold"),
                     text_color=C["mauve"]).pack(side="left")
        ctk.CTkLabel(hdr, text="  Python StabilityMatrix Fork",
                     font=("Segoe UI", 16), text_color=C["subtext"]).pack(
            side="left", pady=(8, 0))
        ctk.CTkLabel(hdr, text=datetime.now().strftime("%d.%m.%Y"),
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            side="right", padx=8)

        # Stat Cards
        self._home_cards = ctk.CTkFrame(f, fg_color=C["bg"])
        self._home_cards.pack(fill="x", pady=(0, 20))

        # SM-Root Info
        section_label(f, "STABILITY MATRIX INSTALLATION").pack(anchor="w", pady=(0, 6))
        self._sm_info_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        self._sm_info_card.pack(fill="x", pady=(0, 16))

        # Quick Launch
        section_label(f, "SCHNELLSTART").pack(anchor="w", pady=(0, 6))
        self._home_packages_frame = ctk.CTkScrollableFrame(
            f, fg_color=C["surface"], corner_radius=12, height=280)
        self._home_packages_frame.pack(fill="x")

        return f

    def _refresh_home(self):
        # Stat Cards
        for w in self._home_cards.winfo_children():
            w.destroy()

        installed = len(self.cfg.packages)
        running = len(self.launcher.get_running_ids())
        sm_ok = self.cfg.sm_root.exists()
        model_root = self.cfg.models_root
        model_count = 0
        if model_root.exists():
            try:
                model_count = sum(1 for f in model_root.rglob("*")
                                  if f.is_file() and f.suffix in
                                  {".safetensors", ".ckpt", ".pt"})
            except Exception:
                pass

        # Disk-Nutzung berechnen
        disk_gb = ""
        if model_root.exists():
            try:
                total_bytes = sum(f.stat().st_size for f in model_root.rglob("*")
                                  if f.is_file())
                disk_gb = f"{total_bytes / 1_073_741_824:.1f} GB"
            except Exception:
                disk_gb = "?"

        stats = [
            ("Pakete",   str(installed),                C["blue"]),
            ("Laufend",  str(running),                  C["green"] if running else C["subtext"]),
            ("Modelle",  str(model_count),              C["teal"]),
            ("Disk",     disk_gb or "–",                C["peach"]),
            ("SM-Root",  "OK" if sm_ok else "FEHLT",   C["green"] if sm_ok else C["red"]),
        ]
        for title, val, color in stats:
            card = ctk.CTkFrame(self._home_cards, fg_color=C["card"], corner_radius=10)
            card.pack(side="left", expand=True, fill="both", padx=4)
            ctk.CTkLabel(card, text=val, font=("Segoe UI", 26, "bold"),
                         text_color=color).pack(pady=(12, 0))
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 10),
                         text_color=C["subtext"]).pack(pady=(0, 12))

        # SM-Info Card
        for w in self._sm_info_card.winfo_children():
            w.destroy()
        row = ctk.CTkFrame(self._sm_info_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(row, text="Pfad:", font=("Segoe UI", 11),
                     text_color=C["subtext"], width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(self.cfg.sm_root),
                     font=("Cascadia Code", 11), text_color=C["blue"]).pack(side="left")
        if sm_ok:
            ctk.CTkButton(row, text="\u2630 Explorer", width=90, height=26,
                          fg_color=C["border"], text_color=C["text"],
                          hover_color=C["surface"], font=("Segoe UI", 10),
                          corner_radius=6,
                          command=lambda: os.startfile(str(self.cfg.sm_root))
                          if sys.platform == "win32" else None).pack(side="right")

        # Quick-Launch Cards
        for w in self._home_packages_frame.winfo_children():
            w.destroy()
        for pkg in self.cfg.packages:
            self._make_pkg_quick_card(self._home_packages_frame, pkg)

    def _make_pkg_quick_card(self, parent, pkg: Package):
        is_running = self.launcher.is_running(pkg.id)
        card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=10)
        card.pack(fill="x", padx=6, pady=3)

        # Status-Indikator
        dot = ctk.CTkLabel(card, text="\u25CF",
                            text_color=C["green"] if is_running else C["subtext"],
                            font=("Segoe UI", 14), width=24)
        dot.pack(side="left", padx=(12, 4))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)

        ctk.CTkLabel(info, text=f"{pkg.icon}  {pkg.display_name}",
                     font=("Segoe UI", 13, "bold"),
                     text_color=pkg.color, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info,
                     text=f"{pkg.package_name}  \u2022  {pkg.version_branch}@{pkg.version_sha}",
                     font=("Segoe UI", 10), text_color=C["subtext"],
                     anchor="w").pack(anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=8)

        if is_running:
            ctk.CTkButton(
                btn_frame, text="\u25A0 Stop", width=72, height=30,
                fg_color=C["red"], text_color=C["bg"],
                hover_color=C["rosewater"], font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=lambda p=pkg: self._stop_package(p),
            ).pack(side="left", padx=2)
            # URL-Button wenn WebUI-URL erkannt wurde
            url = self._detected_urls.get(pkg.id)
            if url:
                ctk.CTkButton(
                    btn_frame, text="\U0001F310 Browser", width=80, height=30,
                    fg_color=C["blue"], text_color=C["bg"],
                    hover_color=C["sky"], font=("Segoe UI", 10, "bold"),
                    corner_radius=8,
                    command=lambda u=url: webbrowser.open(u),
                ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_frame, text="\u2630 Log", width=60, height=30,
                fg_color=C["surface"], text_color=C["text"],
                hover_color=C["border"], font=("Segoe UI", 11),
                corner_radius=8,
                command=lambda p=pkg: self._show_pkg_log(p),
            ).pack(side="left", padx=2)
        else:
            ctk.CTkButton(
                btn_frame, text="\u25B6 Start", width=72, height=30,
                fg_color=C["green"], text_color=C["bg"],
                hover_color=C["teal"], font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=lambda p=pkg: self._start_package(p),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_frame, text="\u2699 Detail", width=72, height=30,
                fg_color=C["surface"], text_color=C["text"],
                hover_color=C["border"], font=("Segoe UI", 11),
                corner_radius=8,
                command=lambda p=pkg: self._open_pkg_detail(p),
            ).pack(side="left", padx=2)

    # ─── Pakete / Launcher ──────────────────────────────────

    def _build_packages(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        # Header-Zeile
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(hdr, text="Pakete & Launcher",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkButton(hdr, text="\u25B6\u25B6 Alle starten",
                      width=110, height=32,
                      fg_color=C["green"], text_color=C["bg"],
                      hover_color=C["teal"], font=("Segoe UI", 11, "bold"),
                      corner_radius=8,
                      command=self._start_all_packages).pack(side="right", padx=4)
        ctk.CTkButton(hdr, text="\u25A0\u25A0 Alle stoppen",
                      width=110, height=32,
                      fg_color=C["red"], text_color=C["bg"],
                      hover_color=C["rosewater"], font=("Segoe UI", 11, "bold"),
                      corner_radius=8,
                      command=self._stop_all_packages).pack(side="right", padx=4)

        ctk.CTkLabel(f, text="WebUI-Pakete starten, konfigurieren und verwalten",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            anchor="w", pady=(0, 8))

        body = ctk.CTkFrame(f, fg_color=C["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        # Linke Spalte: Paketliste
        left = ctk.CTkFrame(body, fg_color=C["surface"], corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        pkg_header = ctk.CTkFrame(left, fg_color="transparent")
        pkg_header.pack(fill="x", padx=8, pady=(10, 4))
        section_label(pkg_header, "INSTALLIERTE PAKETE").pack(side="left")
        self._pkg_search_var = ctk.StringVar()
        self._pkg_search_var.trace_add("write", lambda *_: self._refresh_packages())
        ctk.CTkEntry(pkg_header, textvariable=self._pkg_search_var,
                     placeholder_text="\U0001F50D Suchen...",
                     width=130, height=26,
                     fg_color=C["card"], border_color=C["border"],
                     font=("Segoe UI", 10)).pack(side="right")

        self._pkg_list = ctk.CTkScrollableFrame(left, fg_color=C["surface"],
                                                 corner_radius=0)
        self._pkg_list.pack(fill="both", expand=True)

        # Rechte Spalte: Detail-Panel
        self._pkg_detail = ctk.CTkFrame(body, fg_color=C["surface"], corner_radius=12)
        self._pkg_detail.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(self._pkg_detail,
                     text="Paket auswaehlen um Details zu sehen",
                     font=("Segoe UI", 14), text_color=C["subtext"]).pack(
            expand=True)

        return f

    def _refresh_packages(self):
        for w in self._pkg_list.winfo_children():
            w.destroy()

        query = getattr(self, "_pkg_search_var", None)
        q = query.get().lower().strip() if query else ""

        for pkg in self.cfg.packages:
            # Suchfilter
            if q and q not in pkg.display_name.lower() and q not in pkg.package_name.lower():
                continue

            is_running = self.launcher.is_running(pkg.id)
            card = ctk.CTkFrame(self._pkg_list, fg_color=C["card"],
                                corner_radius=10)
            card.pack(fill="x", padx=6, pady=3)

            dot = ctk.CTkLabel(card, text="\u25CF",
                                text_color=C["green"] if is_running else C["subtext"],
                                font=("Segoe UI", 14), width=22)
            dot.pack(side="left", padx=(10, 4))

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=6)
            ctk.CTkLabel(info, text=pkg.display_name,
                         font=("Segoe UI", 12, "bold"),
                         text_color=pkg.color, anchor="w").pack(anchor="w")

            # URL anzeigen wenn laufend
            url = self._detected_urls.get(pkg.id)
            sub = url if url else pkg.package_name
            sub_color = C["blue"] if url else C["subtext"]
            ctk.CTkLabel(info, text=sub, font=("Segoe UI", 10),
                         text_color=sub_color, anchor="w", cursor="hand2" if url else "arrow").pack(anchor="w")

            # Buttons rechts
            btn_r = ctk.CTkFrame(card, fg_color="transparent")
            btn_r.pack(side="right", padx=4, pady=4)

            if is_running and url:
                ctk.CTkButton(
                    btn_r, text="\U0001F310", width=32, height=28,
                    fg_color=C["blue"], text_color=C["bg"],
                    hover_color=C["sky"], font=("Segoe UI", 12),
                    corner_radius=6,
                    command=lambda u=url: webbrowser.open(u),
                ).pack(side="left", padx=2)

            if is_running:
                badge(btn_r, "\u25CF Lauft", C["green"]).pack(side="left", pady=8, padx=2)

            ctk.CTkButton(
                btn_r, text="Detail", width=66,
                fg_color=C["border"], text_color=C["text"],
                hover_color=C["surface"], font=("Segoe UI", 10),
                height=28, corner_radius=6,
                command=lambda p=pkg: self._open_pkg_detail(p),
            ).pack(side="left", padx=2)

    def _start_all_packages(self):
        started = 0
        for pkg in self.cfg.packages:
            if not self.launcher.is_running(pkg.id) and pkg.is_installed:
                self._start_package(pkg)
                started += 1
        if started == 0:
            self._toast_show("Alle Pakete laufen bereits", C["yellow"])

    def _stop_all_packages(self):
        running = self.launcher.get_running_ids()
        if not running:
            self._toast_show("Kein Paket laeuft", C["subtext"])
            return
        for rid in list(running):
            pkg = next((p for p in self.cfg.packages if p.id == rid), None)
            if pkg:
                self._stop_package(pkg)

    def _open_pkg_detail(self, pkg: Package):
        self._selected_pkg = pkg
        self._navigate(1)

        for w in self._pkg_detail.winfo_children():
            w.destroy()

        is_running = self.launcher.is_running(pkg.id)

        # Header
        hdr = ctk.CTkFrame(self._pkg_detail, fg_color=C["card"],
                            corner_radius=10)
        hdr.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(hdr, text=f"{pkg.icon}  {pkg.display_name}",
                     font=("Segoe UI", 18, "bold"),
                     text_color=pkg.color).pack(anchor="w", padx=16, pady=(10, 4))

        meta = ctk.CTkFrame(hdr, fg_color="transparent")
        meta.pack(fill="x", padx=16, pady=(0, 10))
        for lbl, val in [
            ("Paket:", pkg.package_name),
            ("Branch:", pkg.version_branch),
            ("Commit:", pkg.version_sha),
            ("Python:", pkg.python_version),
            ("Pfad:", str(pkg.abs_path)[:60]),
        ]:
            row = ctk.CTkFrame(meta, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=lbl, font=("Segoe UI", 10, "bold"),
                         text_color=C["subtext"], width=55,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, font=("Cascadia Code", 10),
                         text_color=C["text"], anchor="w").pack(side="left")

        # Aktions-Buttons
        btns = ctk.CTkFrame(self._pkg_detail, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(0, 8))

        if is_running:
            ctk.CTkButton(btns, text="\u25A0  Stoppen", height=38,
                          fg_color=C["red"], text_color=C["bg"],
                          hover_color="#e57185", font=("Segoe UI", 12, "bold"),
                          corner_radius=8, width=120,
                          command=lambda: self._stop_package(pkg)).pack(
                side="left", padx=(0, 8))
            ctk.CTkButton(btns, text="\u2630  Log anzeigen", height=38,
                          fg_color=C["surface"], text_color=C["text"],
                          hover_color=C["border"], font=("Segoe UI", 12),
                          corner_radius=8, width=130,
                          command=lambda: self._show_pkg_log(pkg)).pack(side="left")
        else:
            ctk.CTkButton(btns, text="\u25B6  Starten", height=38,
                          fg_color=C["green"], text_color=C["bg"],
                          hover_color=C["teal"], font=("Segoe UI", 12, "bold"),
                          corner_radius=8, width=120,
                          command=lambda: self._start_package(pkg)).pack(
                side="left", padx=(0, 8))

        if sys.platform == "win32":
            ctk.CTkButton(btns, text="\u2630  Explorer", height=38,
                          fg_color=C["card"], text_color=C["text"],
                          hover_color=C["surface"], font=("Segoe UI", 12),
                          corner_radius=8, width=100,
                          command=lambda: os.startfile(str(pkg.abs_path))
                          if pkg.abs_path.exists() else None).pack(
                side="left", padx=(0, 8))

        # Launch Args Editor
        section_label(self._pkg_detail, "LAUNCH ARGUMENTE").pack(
            anchor="w", padx=12, pady=(8, 4))

        args_frame = ctk.CTkScrollableFrame(self._pkg_detail,
                                             fg_color=C["surface"],
                                             corner_radius=10, height=200)
        args_frame.pack(fill="x", padx=12, pady=(0, 8))

        self._pkg_arg_vars = {}
        for arg in pkg.launch_args:
            row = ctk.CTkFrame(args_frame, fg_color=C["card"], corner_radius=8)
            row.pack(fill="x", padx=4, pady=2)

            name = arg.name or "(extra)"
            ctk.CTkLabel(row, text=name, font=("Cascadia Code", 10),
                         text_color=C["lavender"], width=180, anchor="w").pack(
                side="left", padx=8, pady=6)

            if arg.arg_type == "Bool":
                var = ctk.BooleanVar(value=bool(arg.value))
                sw = ctk.CTkSwitch(row, text="",
                                   variable=var, width=36, height=18,
                                   button_color=C["green"],
                                   progress_color=C["surface"])
                if arg.value:
                    sw.select()
                sw.pack(side="left")
                self._pkg_arg_vars[arg.name] = (arg, var)
            else:
                var = ctk.StringVar(value=str(arg.value) if arg.value else "")
                ctk.CTkEntry(row, textvariable=var, font=("Cascadia Code", 10),
                             fg_color=C["surface"], border_color=C["border"],
                             text_color=C["text"], height=28).pack(
                    side="left", fill="x", expand=True, padx=4)
                self._pkg_arg_vars[arg.name or "(extra)"] = (arg, var)

        # Args speichern
        ctk.CTkButton(
            self._pkg_detail, text="Launch Args speichern",
            fg_color=C["blue"], text_color=C["bg"],
            hover_color=C["sky"], font=("Segoe UI", 11, "bold"),
            height=34, corner_radius=8,
            command=lambda: self._save_pkg_args(pkg),
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Package-Log Preview
        section_label(self._pkg_detail, "PAKET-LOG").pack(
            anchor="w", padx=12, pady=(8, 4))
        self._pkg_log_box = ctk.CTkTextbox(
            self._pkg_detail, font=("Cascadia Code", 9),
            fg_color=C["card"], text_color=C["text"],
            corner_radius=8, height=120, state="disabled",
        )
        self._pkg_log_box.pack(fill="x", padx=12, pady=(0, 12))

        # Existierende Log-Zeilen laden
        buf = self._pkg_log_buffers.get(pkg.id, [])
        if buf:
            self._pkg_log_box.configure(state="normal")
            self._pkg_log_box.insert("end", "\n".join(buf[-50:]))
            self._pkg_log_box.see("end")
            self._pkg_log_box.configure(state="disabled")

    def _save_pkg_args(self, pkg: Package):
        for key, (arg, var) in self._pkg_arg_vars.items():
            if isinstance(var, ctk.BooleanVar):
                arg.value = var.get()
            else:
                arg.value = var.get()
        self.cfg.save_launch_args(pkg.id, pkg.launch_args)
        self._toast_show("Launch Args gespeichert")
        self._log(f"[Gespeichert] Launch Args fuer {pkg.display_name}\n", C["green"])

    # ─── Paket starten/stoppen ──────────────────────────────

    def _start_package(self, pkg: Package):
        if not pkg.is_installed:
            messagebox.showerror("Fehler",
                                 f"Paketordner nicht gefunden:\n{pkg.abs_path}")
            return

        self._log(f"\n{'='*60}\n", C["border"])
        self._log(f"  Starte: {pkg.display_name}\n", C["mauve"])
        self._log(f"  Verzeichnis: {pkg.abs_path}\n", C["subtext"])
        self._log(f"{'='*60}\n\n", C["border"])

        def output_cb(pkg_id: str, line: str, level: str):
            self._pkg_log_buffers.setdefault(pkg_id, []).append(line)
            # Kuerze Buffer auf 500 Zeilen
            buf = self._pkg_log_buffers[pkg_id]
            if len(buf) > 500:
                self._pkg_log_buffers[pkg_id] = buf[-500:]
            col = C["red"] if level == "error" else C["text"]
            self._log(f"[{pkg.display_name}] {line}\n", col)

            # URL erkennen, speichern und Toast
            if "http://" in line or "https://" in line:
                import re as _re
                m = _re.search(r"https?://[^\s,\)]+", line)
                if m:
                    url = m.group(0).rstrip(".")
                    self._detected_urls[pkg.id] = url
                    self.after(0, lambda u=url, n=pkg.display_name: self._toast_show(
                        f"\U0001F310 {n}: {u}", C["blue"], ms=8000))

        ok = self.launcher.start(pkg, output_cb=output_cb)
        if ok:
            self._toast_show(f"{pkg.display_name} gestartet")
            self._update_running_sidebar()
            self.after(500, lambda: self._refresh_packages())
            self.after(500, lambda: self._refresh_home())
        else:
            self._toast_show(f"Start fehlgeschlagen", C["red"])

    def _stop_package(self, pkg: Package):
        self.launcher.stop(pkg.id)
        pkg.process = None
        self._detected_urls.pop(pkg.id, None)   # URL vergessen
        self._toast_show(f"{pkg.display_name} gestoppt", C["yellow"])
        self._log(f"[Stop] {pkg.display_name}\n", C["yellow"])
        self._update_running_sidebar()
        self.after(300, lambda: self._refresh_packages())
        self.after(300, lambda: self._refresh_home())

    def _show_pkg_log(self, pkg: Package):
        self._navigate(6)
        buf = self._pkg_log_buffers.get(pkg.id, [])
        self._log_box.configure(state="normal")
        self._log_box.delete("0.0", "end")
        for line in buf:
            self._log_box.insert("end", line + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _update_running_sidebar(self):
        for w in self._running_frame.winfo_children():
            w.destroy()
        running_ids = self.launcher.get_running_ids()
        if not running_ids:
            ctk.CTkLabel(self._running_frame, text="Keine",
                         font=("Segoe UI", 10), text_color=C["subtext"]).pack(
                anchor="w", padx=4)
            return
        for pid in running_ids:
            pkg = next((p for p in self.cfg.packages if p.id == pid), None)
            if pkg:
                row = ctk.CTkFrame(self._running_frame,
                                   fg_color=C["card"], corner_radius=6)
                row.pack(fill="x", padx=4, pady=1)
                ctk.CTkLabel(row, text=f"\u25CF {pkg.display_name[:16]}",
                             font=("Segoe UI", 10, "bold"),
                             text_color=C["green"]).pack(
                    side="left", padx=6, pady=4)
                # URL-Button wenn vorhanden
                url = self._detected_urls.get(pid)
                if url:
                    ctk.CTkButton(row, text="\U0001F310", width=22, height=20,
                                  fg_color=C["blue"], text_color=C["bg"],
                                  hover_color=C["sky"], font=("Segoe UI", 10),
                                  corner_radius=4,
                                  command=lambda u=url: webbrowser.open(u)).pack(
                        side="right", padx=1)
                ctk.CTkButton(row, text="\u25A0", width=22, height=20,
                              fg_color=C["surface"], text_color=C["red"],
                              hover_color=C["border"], font=("Segoe UI", 10),
                              corner_radius=4,
                              command=lambda p=pkg: self._stop_package(p)).pack(
                    side="right", padx=4)

    # ─── Model Manager ──────────────────────────────────────

    def _build_model_mgr(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])
        ctk.CTkLabel(f, text="Model Manager",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f,
                     text=f"Master-Root: {self.cfg.models_root}",
                     font=("Cascadia Code", 11), text_color=C["blue"]).pack(
            anchor="w", pady=(0, 12))

        if not HAS_MM:
            ctk.CTkLabel(f, text="Model Manager Modul nicht verfuegbar",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(
                anchor="w", pady=20)
            return f

        # Tabs
        tabs = ctk.CTkTabview(f, fg_color=C["bg"], corner_radius=10,
                              segmented_button_fg_color=C["card"],
                              segmented_button_selected_color=C["mauve"],
                              segmented_button_unselected_color=C["surface"])
        tabs.pack(fill="both", expand=True)
        tabs.add("Symlinks anwenden")
        tabs.add("Profile")
        tabs.add("Master-Typen")

        # ── Tab: Symlinks ────────────────────────────────
        sym_tab = tabs.tab("Symlinks anwenden")

        ctrl = ctk.CTkFrame(sym_tab, fg_color=C["bg"])
        ctrl.pack(fill="x", pady=(8, 12))

        self._mm_dry_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl, text="Dry-Run", variable=self._mm_dry_var,
                      font=("Segoe UI", 12), text_color=C["text"],
                      button_color=C["blue"]).pack(side="left")

        ctk.CTkButton(ctrl, text="\u25B6\u25B6 Alle Profile anwenden",
                      fg_color=C["mauve"], text_color=C["bg"],
                      hover_color=C["lavender"], font=("Segoe UI", 12, "bold"),
                      height=38, corner_radius=8,
                      command=self._mm_apply_all).pack(side="right")

        self._mm_log = ctk.CTkTextbox(sym_tab, font=("Cascadia Code", 10),
                                       fg_color=C["card"], text_color=C["text"],
                                       corner_radius=8, state="disabled")
        self._mm_log.pack(fill="both", expand=True)

        # ── Tab: Profile ─────────────────────────────────
        prof_tab = tabs.tab("Profile")
        self._mm_prof_frame = ctk.CTkScrollableFrame(prof_tab, fg_color=C["bg"],
                                                      corner_radius=0)
        self._mm_prof_frame.pack(fill="both", expand=True)
        self._mm_refresh_profiles()

        # ── Tab: Master-Typen ────────────────────────────
        types_tab = tabs.tab("Master-Typen")
        self._mm_types_frame = ctk.CTkScrollableFrame(
            types_tab, fg_color=C["surface"], corner_radius=10)
        self._mm_types_frame.pack(fill="both", expand=True)
        self._mm_refresh_types()

        return f

    def _mm_apply_all(self):
        dry = self._mm_dry_var.get()
        self._mm_log.configure(state="normal")
        self._mm_log.delete("0.0", "end")
        self._mm_log.configure(state="disabled")

        def worker():
            try:
                from app import profiles as _profiles, apply_profile
                ok = skip = err = 0
                for key, prof in _profiles.items():
                    if not prof.get("enabled"):
                        continue
                    self._mm_log_line(f"\u25B6 {prof.get('display_name', key)}\n",
                                      C["mauve"])
                    for status, msg in apply_profile(prof, dry):
                        sym = {
                            "ok": "\u2713", "skip": "\u2500",
                            "dry": "~", "error": "\u2717", "warn": "!"
                        }.get(status, "?")
                        col = {
                            "ok": C["green"], "skip": C["subtext"],
                            "dry": C["teal"], "error": C["red"],
                            "warn": C["yellow"],
                        }.get(status, C["text"])
                        self._mm_log_line(f"   {sym} {msg}\n", col)
                        if status == "ok":   ok += 1
                        elif status == "skip":skip += 1
                        elif status == "error":err += 1
                self._mm_log_line(
                    f"\nFertig: {ok} OK, {skip} uebersprungen, {err} Fehler\n",
                    C["green"] if not err else C["red"])
                self.after(0, lambda: self._toast_show(
                    f"Fertig: {ok} Links erstellt"))
            except Exception as e:
                self._mm_log_line(f"Fehler: {e}\n", C["red"])

        threading.Thread(target=worker, daemon=True).start()

    def _mm_log_line(self, text: str, color: str = None):
        def _do():
            self._mm_log.configure(state="normal")
            if color:
                tag = f"col_{color.replace('#', '')}"
                self._mm_log.tag_config(tag, foreground=color)
                self._mm_log.insert("end", text, tag)
            else:
                self._mm_log.insert("end", text)
            self._mm_log.see("end")
            self._mm_log.configure(state="disabled")
        self.after(0, _do)

    def _mm_refresh_profiles(self):
        for w in self._mm_prof_frame.winfo_children():
            w.destroy()
        try:
            from app import profiles as _profiles
            _profiles_local = dict(_profiles)
        except Exception:
            _profiles_local = {}

        for key, prof in sorted(_profiles_local.items()):
            card = ctk.CTkFrame(self._mm_prof_frame, fg_color=C["card"],
                                corner_radius=10)
            card.pack(fill="x", padx=4, pady=3)

            enabled = prof.get("enabled", True)
            pkg_dir = self.cfg.packages_root / prof.get("package_folder", "")
            found = pkg_dir.exists()

            ctk.CTkLabel(card,
                         text="\u25CF" if enabled else "\u25CB",
                         text_color=C["green"] if (enabled and found) else
                         C["yellow"] if enabled else C["subtext"],
                         font=("Segoe UI", 14), width=22).pack(side="left", padx=(10, 4))

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=6)
            ctk.CTkLabel(info, text=prof.get("display_name", key),
                         font=("Segoe UI", 12, "bold"),
                         text_color=C["text"] if enabled else C["subtext"],
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"{prof.get('package_folder', '')}  "
                              f"\u2022  {len(prof.get('rules', []))} Regeln",
                         font=("Segoe UI", 10), text_color=C["subtext"],
                         anchor="w").pack(anchor="w")

            badge(card, "\u2713" if found else "\u2717",
                  C["green"] if found else C["yellow"]).pack(
                side="right", padx=8, pady=6)

    def _mm_refresh_types(self):
        for w in self._mm_types_frame.winfo_children():
            w.destroy()
        try:
            from app import master_types as _mt, master_folder
            items = sorted(_mt.items())
        except Exception:
            items = []

        for key, mt in items:
            row = ctk.CTkFrame(self._mm_types_frame, fg_color=C["card"],
                               corner_radius=6)
            row.pack(fill="x", padx=4, pady=1)

            try:
                path = self.cfg.models_root / mt.get("folder", key)
                exists = path.exists()
            except Exception:
                exists = False

            ctk.CTkLabel(row, text=key, font=("Cascadia Code", 10),
                         text_color=C["lavender"], width=170,
                         anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=mt.get("folder", ""),
                         font=("Cascadia Code", 10), text_color=C["peach"],
                         width=150, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=mt.get("description", ""),
                         font=("Segoe UI", 10), text_color=C["subtext"],
                         anchor="w").pack(side="left", padx=4, fill="x", expand=True)
            ctk.CTkLabel(row,
                         text="\u2713" if exists else "\u2717",
                         font=("Segoe UI", 10, "bold"),
                         text_color=C["green"] if exists else C["yellow"]).pack(
                side="right", padx=8)

    # ─── Downloader ─────────────────────────────────────────

    def _build_downloader(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])
        ctk.CTkLabel(f, text="Model Downloader",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Modelle von CivitAI oder HuggingFace laden",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            anchor="w", pady=(0, 12))

        if not HAS_DOWNLOADER:
            ctk.CTkLabel(f, text="downloader.py nicht gefunden",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(
                anchor="w")
            return f

        # URL-Eingabe
        url_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        url_card.pack(fill="x", pady=(0, 12))
        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(url_row, text="URL:", font=("Segoe UI", 12, "bold"),
                     text_color=C["text"], width=40).pack(side="left")
        self._pm_dl_url = ctk.StringVar()
        ctk.CTkEntry(url_row, textvariable=self._pm_dl_url,
                     font=("Cascadia Code", 12), fg_color=C["surface"],
                     border_color=C["border"], text_color=C["text"],
                     placeholder_text="https://civitai.com/models/... oder HuggingFace URL").pack(
            side="left", fill="x", expand=True, padx=8)
        ctk.CTkButton(url_row, text="Abrufen", width=90,
                      fg_color=C["blue"], text_color=C["bg"],
                      hover_color=C["sky"], font=("Segoe UI", 12, "bold"),
                      height=34, corner_radius=8,
                      command=self._dl_fetch).pack(side="right")

        # Modell Info
        self._pm_dl_info = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        self._pm_dl_info.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(self._pm_dl_info, text="Gib eine URL ein...",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            padx=16, pady=16)

        # Downloads
        section_label(f, "DOWNLOADS").pack(anchor="w", pady=(4, 6))
        self._pm_dl_queue = ctk.CTkScrollableFrame(
            f, fg_color=C["surface"], corner_radius=12)
        self._pm_dl_queue.pack(fill="both", expand=True)

        self._pm_model_info = None
        self._pm_dl_type_var = ctk.StringVar(value="StableDiffusion")
        self._dl_update_timer()
        return f

    def _dl_fetch(self):
        url = self._pm_dl_url.get().strip()
        if not url:
            return
        for w in self._pm_dl_info.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._pm_dl_info, text="Lade...",
                     font=("Segoe UI", 12), text_color=C["yellow"]).pack(
            padx=16, pady=16)

        def worker():
            try:
                source = detect_source(url)
                if source == "civitai":
                    client = CivitAIClient()
                    mid = client.parse_url(url)
                    info = client.fetch_model(mid)
                elif source == "huggingface":
                    client = HuggingFaceClient()
                    rid = client.parse_url(url)
                    info = client.fetch_model(rid)
                else:
                    raise ValueError("Unbekannte URL (CivitAI/HuggingFace)")
                self.after(0, lambda: self._dl_show_info(info))
            except Exception as e:
                self.after(0, lambda: [w.destroy() for w in self._pm_dl_info.winfo_children()]
                           or ctk.CTkLabel(
                    self._pm_dl_info, text=f"Fehler: {e}",
                    font=("Segoe UI", 12), text_color=C["red"]).pack(
                    padx=16, pady=16))

        threading.Thread(target=worker, daemon=True).start()

    def _dl_show_info(self, info):
        self._pm_model_info = info
        for w in self._pm_dl_info.winfo_children():
            w.destroy()

        grid = ctk.CTkFrame(self._pm_dl_info, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(grid, text=info.name, font=("Segoe UI", 16, "bold"),
                     text_color=C["text"]).pack(anchor="w")

        meta = ctk.CTkFrame(grid, fg_color="transparent")
        meta.pack(fill="x", pady=4)
        badge(meta, info.source.upper(), C["blue"]).pack(side="left", padx=(0, 6))
        badge(meta, info.model_type, C["peach"]).pack(side="left", padx=(0, 6))
        if info.base_model:
            badge(meta, info.base_model, C["teal"]).pack(side="left", padx=(0, 6))

        # Typ-Auswahl
        tr = ctk.CTkFrame(grid, fg_color="transparent")
        tr.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(tr, text="Ziel-Typ:", font=("Segoe UI", 11),
                     text_color=C["subtext"]).pack(side="left")
        self._pm_dl_type_var.set(info.master_type)

        try:
            from app import master_types as _mt
            type_keys = sorted(_mt.keys())
        except Exception:
            type_keys = ["StableDiffusion", "Lora", "VAE", "ControlNet"]

        ctk.CTkComboBox(tr, variable=self._pm_dl_type_var,
                        values=type_keys, font=("Segoe UI", 11), width=200,
                        fg_color=C["surface"], border_color=C["border"]).pack(
            side="left", padx=8)

        # Dateien
        for v in info.versions[:3]:
            ctk.CTkLabel(grid, text=f"Version: {v['name']}",
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["lavender"]).pack(anchor="w", pady=(8, 2))
            for fi in v.get("files", [])[:5]:
                frow = ctk.CTkFrame(grid, fg_color=C["card"], corner_radius=8)
                frow.pack(fill="x", pady=1)
                ctk.CTkLabel(frow, text=fi.get("name", "?"),
                             font=("Cascadia Code", 10),
                             text_color=C["text"], anchor="w").pack(
                    side="left", padx=8, pady=4)
                if fi.get("size"):
                    ctk.CTkLabel(frow, text=fmt_size(fi["size"]),
                                 font=("Segoe UI", 9),
                                 text_color=C["subtext"]).pack(side="left", padx=4)
                if fi.get("url"):
                    ctk.CTkButton(frow, text="\u2B07 DL", width=60,
                                  fg_color=C["green"], text_color=C["bg"],
                                  hover_color=C["teal"],
                                  font=("Segoe UI", 10, "bold"),
                                  height=26, corner_radius=6,
                                  command=lambda u=fi["url"],
                                  n=fi.get("name", "model.safetensors"),
                                  s=fi.get("size", 0):
                                  self._dl_start(u, n, info.name, s)).pack(
                        side="right", padx=6, pady=3)

    def _dl_start(self, url, filename, model_name, size):
        target = self._pm_dl_type_var.get()
        dest = self.cfg.models_root / target.replace("StableDiffusion", "Checkpoints")
        dest.mkdir(parents=True, exist_ok=True)
        self._dl_mgr.add_download(url, dest, filename, model_name, size)
        self._toast_show(f"Download: {filename}")
        self._log(f"[Download] {filename} -> {dest}\n", C["blue"])

    def _on_dl_complete(self, task):
        if task.status == "complete":
            self.after(0, lambda: self._toast_show(
                f"Fertig: {task.filename}", C["green"]))

    def _dl_update_timer(self):
        if self._active_idx == 3 and self._dl_mgr:
            self._refresh_dl_queue()
        self.after(1000, self._dl_update_timer)

    def _refresh_dl_queue(self):
        if not self._dl_mgr:
            return
        for w in self._pm_dl_queue.winfo_children():
            w.destroy()
        tasks = list(self._dl_mgr.tasks)
        if not tasks:
            ctk.CTkLabel(self._pm_dl_queue,
                         text="Keine Downloads",
                         font=("Segoe UI", 12), text_color=C["subtext"]).pack(
                padx=16, pady=12)
            return
        for task in reversed(tasks):
            card = ctk.CTkFrame(self._pm_dl_queue, fg_color=C["card"],
                                corner_radius=10)
            card.pack(fill="x", padx=4, pady=2)
            icons = {"queued": "\u23F3", "downloading": "\u2B07",
                     "complete": "\u2713", "error": "\u2717", "cancelled": "\u2716"}
            colors = {"queued": C["subtext"], "downloading": C["blue"],
                      "complete": C["green"], "error": C["red"],
                      "cancelled": C["yellow"]}
            icon = icons.get(task.status, "?")
            color = colors.get(task.status, C["text"])
            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 16),
                         text_color=color, width=28).pack(side="left", padx=(10, 4))
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=6)
            ctk.CTkLabel(info, text=task.filename,
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")
            if task.status == "downloading":
                pb = ctk.CTkProgressBar(info, height=5, fg_color=C["surface"],
                                        progress_color=C["blue"])
                pb.pack(fill="x", pady=(2, 0))
                pb.set(task.progress)
                ctk.CTkLabel(info,
                             text=f"{fmt_size(task.downloaded)} / {fmt_size(task.file_size)}"
                                  f"  |  {fmt_speed(task.speed)}",
                             font=("Segoe UI", 9),
                             text_color=C["subtext"]).pack(anchor="w")

    # ─── Scanner ────────────────────────────────────────────

    def _build_scanner(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])
        ctk.CTkLabel(f, text="Model Scanner",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Disk-Analyse und Duplikat-Erkennung",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            anchor="w", pady=(0, 12))

        if not HAS_SCANNER:
            ctk.CTkLabel(f, text="scanner.py nicht gefunden",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(anchor="w")
            return f

        btn_row = ctk.CTkFrame(f, fg_color=C["bg"])
        btn_row.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(btn_row, text="Ordnergroessen",
                      fg_color=C["teal"], text_color=C["bg"],
                      hover_color=C["green"], font=("Segoe UI", 12, "bold"),
                      height=38, corner_radius=8,
                      command=self._scan_sizes).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Duplikate finden",
                      fg_color=C["peach"], text_color=C["bg"],
                      hover_color=C["yellow"], font=("Segoe UI", 12, "bold"),
                      height=38, corner_radius=8,
                      command=self._scan_dupes).pack(side="left")

        self._sc_prog = ctk.CTkProgressBar(f, height=5, fg_color=C["surface"],
                                            progress_color=C["teal"])
        self._sc_prog.pack(fill="x", pady=(0, 4))
        self._sc_prog.set(0)
        self._sc_status = ctk.CTkLabel(f, text="Bereit",
                                        font=("Segoe UI", 10),
                                        text_color=C["subtext"])
        self._sc_status.pack(anchor="w", pady=(0, 8))

        self._sc_results = ctk.CTkScrollableFrame(f, fg_color=C["surface"],
                                                   corner_radius=12)
        self._sc_results.pack(fill="both", expand=True)
        return f

    def _scan_sizes(self):
        self._sc_status.configure(text="Scanne...", text_color=C["teal"])
        self._sc_prog.set(0)

        def prog(done, total, name):
            self.after(0, lambda: self._sc_prog.set(done / max(total, 1)))

        def worker():
            try:
                from app import master_types as _mt
                results = scan_folder_sizes(
                    str(self.cfg.models_root), _mt, prog)
                self.after(0, lambda: self._show_sizes(results))
            except Exception as e:
                self.after(0, lambda: self._sc_status.configure(
                    text=f"Fehler: {e}", text_color=C["red"]))

        threading.Thread(target=worker, daemon=True).start()

    def _show_sizes(self, results):
        for w in self._sc_results.winfo_children():
            w.destroy()
        total = sum(r.total_bytes for r in results)
        ctk.CTkLabel(self._sc_results,
                     text=f"Gesamt: {scan_fmt_size(total)}",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=8, pady=(4, 8))

        for r in sorted(results, key=lambda x: -x.total_bytes):
            row = ctk.CTkFrame(self._sc_results, fg_color=C["card"], corner_radius=6)
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=r.label, font=("Segoe UI", 10),
                         text_color=C["text"], width=140, anchor="w").pack(
                side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=scan_fmt_size(r.total_bytes),
                         font=("Segoe UI", 10, "bold"),
                         text_color=C["green"] if r.total_bytes > 0 else C["subtext"],
                         width=80).pack(side="left")
            ctk.CTkLabel(row, text=f"{r.model_count} Modelle",
                         font=("Segoe UI", 9), text_color=C["subtext"]).pack(side="left")

        self._sc_status.configure(text=f"Fertig: {scan_fmt_size(total)}",
                                   text_color=C["green"])
        self._sc_prog.set(1.0)

    def _scan_dupes(self):
        self._sc_status.configure(text="Suche Duplikate...",
                                   text_color=C["peach"])

        def prog(done, total, name):
            self.after(0, lambda: self._sc_prog.set(done / max(total, 1)))

        def worker():
            dupes = find_duplicates(str(self.cfg.models_root), prog)
            self.after(0, lambda: self._show_dupes(dupes))

        threading.Thread(target=worker, daemon=True).start()

    def _show_dupes(self, dupes):
        for w in self._sc_results.winfo_children():
            w.destroy()
        if not dupes:
            ctk.CTkLabel(self._sc_results, text="Keine Duplikate!",
                         font=("Segoe UI", 14, "bold"),
                         text_color=C["green"]).pack(padx=16, pady=20)
            self._sc_status.configure(text="Keine Duplikate", text_color=C["green"])
            self._sc_prog.set(1.0)
            return
        wasted = sum(g.size * (len(g.files) - 1) for g in dupes)
        ctk.CTkLabel(self._sc_results,
                     text=f"{len(dupes)} Gruppen, {scan_fmt_size(wasted)} verschwendet",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C["yellow"]).pack(anchor="w", padx=8, pady=(4, 8))
        for g in dupes:
            card = ctk.CTkFrame(self._sc_results, fg_color=C["card"], corner_radius=8)
            card.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(card, text=f"{scan_fmt_size(g.size)} x {len(g.files)} Dateien",
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["peach"]).pack(anchor="w", padx=12, pady=(6, 2))
            for fp in g.files:
                ctk.CTkLabel(card, text=str(fp), font=("Cascadia Code", 9),
                             text_color=C["subtext"], anchor="w").pack(
                    anchor="w", padx=12, pady=1)
        self._sc_status.configure(
            text=f"{len(dupes)} Duplikate, {scan_fmt_size(wasted)} verschwendet",
            text_color=C["peach"])
        self._sc_prog.set(1.0)

    # ─── Einstellungen ──────────────────────────────────────

    def _build_settings(self) -> ctk.CTkFrame:
        f = ctk.CTkScrollableFrame(self.main, fg_color=C["bg"])
        ctk.CTkLabel(f, text="\u2699  Einstellungen",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="PyMatrix v" + VERSION,
                     font=("Segoe UI", 11), text_color=C["subtext"]).pack(
            anchor="w", pady=(0, 16))

        def _settings_row(parent, label: str, var, is_path=False, is_secret=False):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 12),
                         text_color=C["text"], width=160, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, textvariable=var,
                                 font=("Cascadia Code", 11),
                                 fg_color=C["surface"], border_color=C["border"],
                                 text_color=C["text"],
                                 show="*" if is_secret else "")
            entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
            if is_path:
                ctk.CTkButton(row, text="\U0001F4C2", width=34, height=30,
                              fg_color=C["surface"], hover_color=C["border"],
                              text_color=C["text"], font=("Segoe UI", 14),
                              command=lambda v=var: (d := filedialog.askdirectory())
                              and v.set(d)).pack(side="left")
            return entry

        # ── Stability Matrix ──────────────────────────────
        section_label(f, "STABILITY MATRIX INSTALLATION").pack(anchor="w", pady=(0, 6))
        sm_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        sm_card.pack(fill="x", pady=(0, 12))
        self._sm_root_var = ctk.StringVar(value=str(self.cfg.sm_root))
        _settings_row(sm_card, "SM-Root Ordner:", self._sm_root_var, is_path=True)

        # ── API Keys ─────────────────────────────────────
        section_label(f, "API KEYS").pack(anchor="w", pady=(8, 6))
        api_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        api_card.pack(fill="x", pady=(0, 12))

        # CivitAI API Key laden
        civitai_key = ""
        hf_token = ""
        try:
            settings_path = Path(__file__).parent / ".." / "model_manager" / "config" / "settings.json"
            if settings_path.exists():
                s = json.loads(settings_path.read_text(encoding="utf-8"))
                civitai_key = s.get("civitai_api_key", "")
                hf_token = s.get("hf_token", "")
        except Exception:
            pass

        self._civitai_key_var = ctk.StringVar(value=civitai_key)
        self._hf_token_var = ctk.StringVar(value=hf_token)
        _settings_row(api_card, "CivitAI API Key:", self._civitai_key_var, is_secret=True)
        ctk.CTkLabel(api_card, text="  Benötigt für Modell-Metadaten und NSFW-Inhalte",
                     font=("Segoe UI", 10), text_color=C["subtext"]).pack(
            anchor="w", padx=16, pady=(0, 4))
        _settings_row(api_card, "HuggingFace Token:", self._hf_token_var, is_secret=True)
        ctk.CTkLabel(api_card, text="  Benötigt für private/gated Modelle",
                     font=("Segoe UI", 10), text_color=C["subtext"]).pack(
            anchor="w", padx=16, pady=(0, 8))

        # ── App-Einstellungen ────────────────────────────
        section_label(f, "ANWENDUNG").pack(anchor="w", pady=(8, 6))
        app_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        app_card.pack(fill="x", pady=(0, 12))

        # Erscheinungsbild
        row_app = ctk.CTkFrame(app_card, fg_color="transparent")
        row_app.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(row_app, text="Erscheinungsbild:", font=("Segoe UI", 12),
                     text_color=C["text"], width=160, anchor="w").pack(side="left")
        self._theme_var = ctk.StringVar(value="dark")
        ctk.CTkSegmentedButton(row_app, values=["dark", "light", "system"],
                               variable=self._theme_var,
                               command=lambda v: ctk.set_appearance_mode(v),
                               fg_color=C["surface"],
                               selected_color=C["mauve"],
                               font=("Segoe UI", 11)).pack(side="left")

        # SM Explorer
        if sys.platform == "win32":
            row_exp = ctk.CTkFrame(app_card, fg_color="transparent")
            row_exp.pack(fill="x", padx=16, pady=(0, 10))
            ctk.CTkLabel(row_exp, text="SM-Ordner öffnen:", font=("Segoe UI", 12),
                         text_color=C["text"], width=160, anchor="w").pack(side="left")
            ctk.CTkButton(row_exp, text="\U0001F4C2 Im Explorer öffnen",
                          width=180, height=30,
                          fg_color=C["surface"], text_color=C["text"],
                          hover_color=C["border"], font=("Segoe UI", 11),
                          corner_radius=6,
                          command=lambda: os.startfile(str(self.cfg.sm_root))
                          if self.cfg.sm_root.exists() else None).pack(side="left")

        # ── Speichern-Button ─────────────────────────────
        ctk.CTkButton(f, text="\U0001F4BE  Einstellungen speichern",
                      fg_color=C["blue"], text_color=C["bg"],
                      hover_color=C["sky"], font=("Segoe UI", 13, "bold"),
                      height=42, corner_radius=10,
                      command=self._save_settings).pack(anchor="w", pady=12)

        # ── Info-Box ─────────────────────────────────────
        info = ctk.CTkFrame(f, fg_color=C["surface"], corner_radius=12)
        info.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(info, text=(
            f"  {APP_NAME} v{VERSION}  •  Python {sys.version.split()[0]}\n"
            "  Liest StabilityMatrix settings.json und startet WebUI-Pakete.\n"
            "  Aenderungen werden in settings.json zurueckgeschrieben."
        ), font=("Segoe UI", 11), text_color=C["subtext"],
                     justify="left").pack(padx=16, pady=12)
        return f

    def _save_settings(self):
        new_root = Path(self._sm_root_var.get())
        self.cfg.sm_root = new_root
        self.cfg.load()

        # API Keys speichern
        try:
            settings_path = Path(__file__).parent / ".." / "model_manager" / "config" / "settings.json"
            if settings_path.exists():
                s = json.loads(settings_path.read_text(encoding="utf-8"))
            else:
                s = {}
            s["civitai_api_key"] = self._civitai_key_var.get()
            s["hf_token"] = self._hf_token_var.get()
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            self._log(f"[Settings] API-Key speichern fehlgeschlagen: {e}\n", C["yellow"])

        self._toast_show("\U0001F4BE Einstellungen gespeichert", C["green"])

    # ─── Log ────────────────────────────────────────────────

    def _build_log(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        # Header-Zeile
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(hdr, text="\u2630  System-Log",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")

        # Buttons rechts
        def _clear_log():
            self._log_box.configure(state="normal")
            self._log_box.delete("0.0", "end")
            self._log_box.configure(state="disabled")

        def _copy_log():
            content = self._log_box.get("0.0", "end")
            self.clipboard_clear()
            self.clipboard_append(content)
            self._toast_show("Log in Zwischenablage kopiert", C["teal"])

        def _save_log():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text", "*.txt"), ("Alle", "*.*")],
                initialfile=f"pymatrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            )
            if path:
                try:
                    Path(path).write_text(
                        self._log_box.get("0.0", "end"), encoding="utf-8")
                    self._toast_show(f"Log gespeichert: {Path(path).name}", C["green"])
                except Exception as e:
                    self._toast_show(f"Fehler: {e}", C["red"])

        ctk.CTkButton(hdr, text="Leeren", width=72, height=30,
                      fg_color=C["card"], text_color=C["subtext"],
                      hover_color=C["surface"], font=("Segoe UI", 11),
                      corner_radius=8, command=_clear_log).pack(side="right", padx=3)
        ctk.CTkButton(hdr, text="\U0001F4CB Kopieren", width=96, height=30,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["surface"], font=("Segoe UI", 11),
                      corner_radius=8, command=_copy_log).pack(side="right", padx=3)
        ctk.CTkButton(hdr, text="\U0001F4BE Speichern", width=100, height=30,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["surface"], font=("Segoe UI", 11),
                      corner_radius=8, command=_save_log).pack(side="right", padx=3)

        # Such- / Filter-Zeile
        ctrl = ctk.CTkFrame(f, fg_color=C["bg"])
        ctrl.pack(fill="x", pady=(0, 6))

        # Paket-Filter
        pkg_names = ["Alle Pakete"] + [p.display_name for p in self.cfg.packages]
        self._log_filter_var = ctk.StringVar(value="Alle Pakete")
        ctk.CTkLabel(ctrl, text="Paket:", font=("Segoe UI", 11),
                     text_color=C["subtext"]).pack(side="left")
        ctk.CTkComboBox(ctrl, variable=self._log_filter_var,
                        values=pkg_names, width=200,
                        fg_color=C["surface"], border_color=C["border"],
                        font=("Segoe UI", 11),
                        command=lambda v: self._apply_log_filter()
                        ).pack(side="left", padx=(4, 12))

        # Suchfeld
        self._log_search_var = ctk.StringVar()
        ctk.CTkLabel(ctrl, text="Suche:", font=("Segoe UI", 11),
                     text_color=C["subtext"]).pack(side="left")
        ctk.CTkEntry(ctrl, textvariable=self._log_search_var,
                     placeholder_text="\U0001F50D in Log suchen...",
                     width=200, height=28,
                     fg_color=C["card"], border_color=C["border"],
                     font=("Segoe UI", 11)).pack(side="left", padx=4)
        ctk.CTkButton(ctrl, text="Suchen", width=70, height=28,
                      fg_color=C["teal"], text_color=C["bg"],
                      hover_color=C["green"], font=("Segoe UI", 11),
                      corner_radius=6,
                      command=self._apply_log_filter).pack(side="left", padx=4)

        self._log_box = ctk.CTkTextbox(
            f, font=("Cascadia Code", 11),
            fg_color=C["card"], text_color=C["text"],
            corner_radius=12, state="disabled",
        )
        self._log_box.pack(fill="both", expand=True)

        # Timestamp-Anzeige toggle
        self._log_timestamps_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Zeitstempel anzeigen",
                        variable=self._log_timestamps_var,
                        font=("Segoe UI", 10), text_color=C["subtext"],
                        fg_color=C["mauve"],
                        checkmark_color=C["bg"]).pack(anchor="e", pady=(4, 0))
        return f

    def _apply_log_filter(self):
        """Zeigt den Log-Buffer gefiltert nach Paket und Suchtext."""
        pkg_filter = getattr(self, "_log_filter_var", None)
        search = getattr(self, "_log_search_var", None)
        if not pkg_filter or not search:
            return

        pkg_name = pkg_filter.get()
        query = search.get().lower().strip()

        # Alle Log-Puffer zusammenführen oder filtern
        if pkg_name == "Alle Pakete":
            all_lines = []
            for pid, buf in self._pkg_log_buffers.items():
                pkg = next((p for p in self.cfg.packages if p.id == pid), None)
                name = pkg.display_name if pkg else pid
                for line in buf:
                    all_lines.append(f"[{name}] {line}")
        else:
            pkg = next((p for p in self.cfg.packages
                        if p.display_name == pkg_name), None)
            if pkg:
                all_lines = self._pkg_log_buffers.get(pkg.id, [])
            else:
                all_lines = []

        if query:
            all_lines = [l for l in all_lines if query in l.lower()]

        self._log_box.configure(state="normal")
        self._log_box.delete("0.0", "end")
        for line in all_lines[-1000:]:
            self._log_box.insert("end", line + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _log(self, text: str, color: str = None):
        def _do():
            self._log_box.configure(state="normal")
            # Timestamp voranstellen wenn aktiviert
            ts_var = getattr(self, "_log_timestamps_var", None)
            if ts_var and ts_var.get() and text.strip():
                ts = datetime.now().strftime("%H:%M:%S")
                prefix = f"[{ts}] "
                tag_ts = "col_ts"
                self._log_box.tag_config(tag_ts, foreground=C["subtext"])
                self._log_box.insert("end", prefix, tag_ts)
            if color:
                tag = f"col_{color.replace('#', '')}"
                self._log_box.tag_config(tag, foreground=color)
                self._log_box.insert("end", text, tag)
            else:
                self._log_box.insert("end", text)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _do)

    # ─── Paket Output ───────────────────────────────────────

    def _on_pkg_output(self, pkg_id: str, line: str, level: str):
        self._pkg_log_buffers.setdefault(pkg_id, []).append(line)
        buf = self._pkg_log_buffers[pkg_id]
        if len(buf) > 500:
            self._pkg_log_buffers[pkg_id] = buf[-500:]
        col = C["red"] if level == "error" else C["text"]
        self._log(f"{line}\n", col)

    # ─── Status-Timer ───────────────────────────────────────

    def _status_timer(self):
        running = self.launcher.get_running_ids()
        running_names = []
        for rid in running:
            pkg = next((p for p in self.cfg.packages if p.id == rid), None)
            if pkg:
                running_names.append(pkg.display_name)

        if running_names:
            self._sb_left.configure(
                text=f"\u25CF Laufend: {', '.join(running_names)}",
                text_color=C["green"])
        else:
            sm_ok = self.cfg.sm_root.exists()
            self._sb_left.configure(
                text=f"{len(self.cfg.packages)} Pakete  |  "
                     f"SM-Root: {'OK' if sm_ok else 'FEHLT'}",
                text_color=C["subtext"] if sm_ok else C["red"])

        # Sidebar-Running-Frame
        self._update_running_sidebar()
        self.after(2000, self._status_timer)

    # ─── Paket Browser ──────────────────────────────────────

    def _build_pkg_browser(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        # Header
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(hdr, text="Paket Browser",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(hdr, text="  Neue WebUIs und Training-Tools installieren",
                     font=("Segoe UI", 13), text_color=C["subtext"]).pack(
            side="left", pady=(8, 0))
        ctk.CTkButton(hdr, text="\u21BB Aktualisieren", width=120, height=32,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["surface"], font=("Segoe UI", 11),
                      corner_radius=8,
                      command=self._refresh_pkg_browser).pack(side="right")

        if not HAS_INSTALLER:
            ctk.CTkLabel(f, text="installer.py nicht gefunden",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(
                anchor="w", pady=20)
            return f

        # ── Obere Steuerleiste: Installiert-Button + Suche + Filter ──
        ctrl_bar = ctk.CTkFrame(f, fg_color=C["bg"])
        ctrl_bar.pack(fill="x", pady=(0, 8))

        # "Installierte Pakete" prominent ganz links
        self._pb_filter = ctk.StringVar(value="installed")
        ctk.CTkButton(ctrl_bar, text="\u2714 Installierte Pakete",
                      width=160, height=34,
                      fg_color=C["green"], text_color=C["bg"],
                      hover_color=C["teal"], font=("Segoe UI", 12, "bold"),
                      corner_radius=8,
                      command=lambda: (self._pb_filter.set("installed"),
                                       self._refresh_pkg_browser())
                      ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(ctrl_bar, text="Alle",     width=66, height=34,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["mauve"], font=("Segoe UI", 11), corner_radius=6,
                      command=lambda: (self._pb_filter.set("all"), self._refresh_pkg_browser())
                      ).pack(side="left", padx=2)
        ctk.CTkButton(ctrl_bar, text="WebUI",    width=66, height=34,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["mauve"], font=("Segoe UI", 11), corner_radius=6,
                      command=lambda: (self._pb_filter.set("webui"), self._refresh_pkg_browser())
                      ).pack(side="left", padx=2)
        ctk.CTkButton(ctrl_bar, text="Training", width=80, height=34,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["mauve"], font=("Segoe UI", 11), corner_radius=6,
                      command=lambda: (self._pb_filter.set("training"), self._refresh_pkg_browser())
                      ).pack(side="left", padx=2)

        # Suchfeld rechts
        self._pb_search_var = ctk.StringVar()
        self._pb_search_var.trace_add("write", lambda *_: self._refresh_pkg_browser())
        ctk.CTkEntry(ctrl_bar, textvariable=self._pb_search_var,
                     placeholder_text="\U0001F50D Paket suchen...",
                     width=200, height=34,
                     fg_color=C["card"], border_color=C["border"],
                     font=("Segoe UI", 11)).pack(side="right")

        # Fortschritts-Bereich
        self._pb_prog_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=10)
        self._pb_prog_card.pack(fill="x", pady=(0, 8))
        self._pb_prog_card.pack_forget()

        self._pb_prog = ctk.CTkProgressBar(self._pb_prog_card, height=8,
                                             fg_color=C["surface"],
                                             progress_color=C["mauve"])
        self._pb_prog_label = ctk.CTkLabel(self._pb_prog_card, text="",
                                            font=("Segoe UI", 11),
                                            text_color=C["text"])

        # Paketliste
        self._pb_list = ctk.CTkScrollableFrame(f, fg_color=C["bg"], corner_radius=0)
        self._pb_list.pack(fill="both", expand=True)

        return f

    def _refresh_pkg_browser(self):
        if not HAS_INSTALLER:
            return
        for w in self._pb_list.winfo_children():
            w.destroy()

        fil = getattr(self, "_pb_filter", None)
        fval = fil.get() if fil else "installed"
        q = getattr(self, "_pb_search_var", None)
        query = q.get().lower().strip() if q else ""

        # Installierte Pakete ermitteln
        installed_names = {p.package_name.lower() for p in self.cfg.packages}

        pkgs = list(PACKAGE_CATALOG.values())
        if fval == "webui":
            pkgs = get_webui_packages()
        elif fval == "training":
            pkgs = get_training_packages()
        elif fval == "installed":
            pkgs = [p for p in pkgs if p.name.lower() in installed_names]

        # Suchfilter
        if query:
            pkgs = [p for p in pkgs if query in p.display_name.lower()
                    or query in p.name.lower() or query in p.description.lower()
                    or any(query in t for t in p.tags)]

        if not pkgs:
            ctk.CTkLabel(self._pb_list,
                         text="Keine Pakete gefunden" if query else "Keine installierten Pakete",
                         font=("Segoe UI", 13), text_color=C["subtext"]).pack(pady=30)
            return

        # Installierte zuerst (immer oben) — außer bei Training-Filter
        if fval in ("all", "webui"):
            inst_pkgs = [p for p in pkgs if p.name.lower() in installed_names and not p.is_training]
            other_webui = [p for p in pkgs if p.name.lower() not in installed_names and not p.is_training]
            training_pkgs = [p for p in pkgs if p.is_training]
            if inst_pkgs:
                section_label(self._pb_list, f"INSTALLIERT ({len(inst_pkgs)})").pack(
                    anchor="w", padx=4, pady=(8, 4))
                for pkg_def in inst_pkgs:
                    self._make_pkg_catalog_card(self._pb_list, pkg_def, installed_names)
            if other_webui:
                section_label(self._pb_list, "WEB INTERFACES").pack(
                    anchor="w", padx=4, pady=(12, 4))
                for pkg_def in other_webui:
                    self._make_pkg_catalog_card(self._pb_list, pkg_def, installed_names)
            if training_pkgs:
                section_label(self._pb_list, "TRAINING TOOLS").pack(
                    anchor="w", padx=4, pady=(12, 4))
                for pkg_def in training_pkgs:
                    self._make_pkg_catalog_card(self._pb_list, pkg_def, installed_names)
        else:
            # Installiert oder Training: direkt anzeigen
            webui_pkgs = [p for p in pkgs if not p.is_training]
            training_pkgs = [p for p in pkgs if p.is_training]
            if webui_pkgs:
                lbl = "INSTALLIERTE WEB INTERFACES" if fval == "installed" else "WEB INTERFACES"
                section_label(self._pb_list, lbl).pack(anchor="w", padx=4, pady=(8, 4))
                for pkg_def in webui_pkgs:
                    self._make_pkg_catalog_card(self._pb_list, pkg_def, installed_names)
            if training_pkgs:
                lbl = "INSTALLIERTE TRAINING TOOLS" if fval == "installed" else "TRAINING TOOLS"
                section_label(self._pb_list, lbl).pack(anchor="w", padx=4, pady=(12, 4))
                for pkg_def in training_pkgs:
                    self._make_pkg_catalog_card(self._pb_list, pkg_def, installed_names)

    def _make_pkg_catalog_card(self, parent, pkg_def, installed_names: set):
        is_installed = pkg_def.name.lower() in installed_names
        card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=10)
        card.pack(fill="x", padx=4, pady=3)

        # Farb-Streifen links
        stripe = ctk.CTkFrame(card, width=4, fg_color=pkg_def.color,
                               corner_radius=4)
        stripe.pack(side="left", fill="y", padx=(0, 10), pady=6)

        # Icon + Info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)

        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(fill="x", anchor="w")
        ctk.CTkLabel(name_row, text=f"{pkg_def.icon}  {pkg_def.display_name}",
                     font=("Segoe UI", 13, "bold"),
                     text_color=pkg_def.color, anchor="w").pack(side="left")

        for tag in pkg_def.tags[:3]:
            ctk.CTkLabel(name_row, text=tag, font=("Segoe UI", 9),
                         fg_color=C["surface"], text_color=C["subtext"],
                         corner_radius=4, padx=4).pack(
                side="left", padx=3)

        ctk.CTkLabel(info, text=pkg_def.description[:120],
                     font=("Segoe UI", 10), text_color=C["subtext"],
                     anchor="w", wraplength=500, justify="left").pack(
            anchor="w", padx=0, pady=(2, 0))
        ctk.CTkLabel(info, text=f"github.com/{pkg_def.github_repo}  •  {pkg_def.branch}",
                     font=("Cascadia Code", 9), text_color=C["border"],
                     anchor="w").pack(anchor="w")

        # Rechte Seite: Buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        if is_installed:
            badge(btn_frame, "✓ Installiert", C["green"]).pack(pady=(0, 4))
            ctk.CTkButton(
                btn_frame, text="⟳ Update",
                width=90, height=28,
                fg_color=C["teal"], text_color=C["bg"],
                hover_color=C["green"], font=("Segoe UI", 10, "bold"),
                corner_radius=6,
                command=lambda p=pkg_def: self._pkg_update_dialog(p),
            ).pack(pady=1)
        else:
            ctk.CTkButton(
                btn_frame, text="⬇ Installieren",
                width=110, height=32,
                fg_color=C["mauve"], text_color=C["bg"],
                hover_color=C["lavender"], font=("Segoe UI", 11, "bold"),
                corner_radius=6,
                command=lambda p=pkg_def: self._pkg_install_dialog(p),
            ).pack()

    def _pkg_install_dialog(self, pkg_def):
        """Zeigt Installations-Dialog und startet Installation."""
        if not self._installer:
            return
        # Bestaetigungsdialog
        ok = messagebox.askyesno(
            "Paket installieren",
            f"'{pkg_def.display_name}' installieren?\n\n"
            f"Quelle: github.com/{pkg_def.github_repo}\n"
            f"Verzeichnis: {self.cfg.packages_root / pkg_def.name}\n\n"
            f"Dies laedt das GitHub-Archiv herunter und erstellt\n"
            f"eine Python-Virtual-Environment."
        )
        if not ok:
            return

        # Progress-Karte anzeigen
        self._pb_prog_card.pack(fill="x", pady=(0, 8))
        self._pb_prog.pack(fill="x", padx=16, pady=(10, 4))
        self._pb_prog.set(0)
        self._pb_prog_label.configure(text=f"Installiere {pkg_def.display_name}...")
        self._pb_prog_label.pack(anchor="w", padx=16, pady=(0, 10))

        def progress_cb(step: str, pct: float, msg: str):
            def _do():
                self._pb_prog_label.configure(text=f"[{step}] {msg}")
                if pct >= 0:
                    self._pb_prog.set(pct / 100)
            self.after(0, _do)

        def done_cb(result):
            def _do():
                self._pb_prog_card.pack_forget()
                if result.success:
                    warn_txt = ""
                    if result.warnings:
                        warn_txt = "\n\nWarnungen:\n" + "\n".join(result.warnings[:3])
                    self._toast_show(f"{pkg_def.display_name} installiert!", C["green"])
                    self._log(f"[Install] {pkg_def.display_name} OK{warn_txt}\n", C["green"])
                    # Symlinks einrichten
                    if self._sf_manager:
                        errs = self._sf_manager.apply_links(
                            pkg_def, result.install_path)
                        if errs:
                            self._log(f"[Links] Fehler: {', '.join(errs)}\n", C["yellow"])
                        else:
                            self._log(f"[Links] Shared Folders verknuepft\n", C["teal"])
                    self.cfg.load()
                    self._refresh_pkg_browser()
                    self._refresh_home()
                else:
                    self._toast_show(f"Fehler: {result.error[:50]}", C["red"])
                    self._log(f"[Install Fehler] {result.error}\n", C["red"])
            self.after(0, _do)

        self._installer.install(pkg_def, progress_cb=progress_cb, done_cb=done_cb)

    def _pkg_update_dialog(self, pkg_def):
        """Sucht das installierte Paket und startet Update."""
        if not self._installer:
            return
        pkg = next((p for p in self.cfg.packages
                    if p.package_name.lower() == pkg_def.name.lower()), None)
        if not pkg:
            self._toast_show("Paket nicht in settings.json gefunden", C["yellow"])
            return

        self._pb_prog_card.pack(fill="x", pady=(0, 8))
        self._pb_prog.pack(fill="x", padx=16, pady=(10, 4))
        self._pb_prog.set(0)
        self._pb_prog_label.configure(text=f"Aktualisiere {pkg_def.display_name}...")
        self._pb_prog_label.pack(anchor="w", padx=16, pady=(0, 10))

        def progress_cb(step: str, pct: float, msg: str):
            def _do():
                self._pb_prog_label.configure(text=f"[{step}] {msg}")
                if pct >= 0:
                    self._pb_prog.set(pct / 100)
            self.after(0, _do)

        def done_cb(result):
            def _do():
                self._pb_prog_card.pack_forget()
                if result.success:
                    self._toast_show(
                        f"Update auf {result.new_sha}", C["green"])
                    self._log(f"[Update] {pkg_def.display_name} → {result.new_sha}\n",
                              C["green"])
                    self.cfg.load()
                    self._refresh_pkg_browser()
                else:
                    self._toast_show(f"Update Fehler: {result.error[:50]}", C["red"])
            self.after(0, _do)

        self._installer.update(
            pkg_def, pkg.abs_path,
            current_sha=pkg.version_sha,
            progress_cb=progress_cb, done_cb=done_cb)

    # ─── Extension Manager ───────────────────────────────────

    def _build_ext_manager(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        # Header
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(hdr, text="Extension Manager",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(hdr, text="  ComfyUI Custom Nodes & A1111/Forge Extensions",
                     font=("Segoe UI", 13), text_color=C["subtext"]).pack(
            side="left", pady=(8, 0))

        if not HAS_EXT:
            ctk.CTkLabel(f, text="extensions.py nicht gefunden",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(
                anchor="w", pady=20)
            return f

        # Tabs: Installiert | ComfyUI Katalog | A1111 Katalog | LoRA Manager
        self._ext_tabs = ctk.CTkTabview(
            f, fg_color=C["bg"], corner_radius=10,
            segmented_button_fg_color=C["card"],
            segmented_button_selected_color=C["mauve"],
            segmented_button_unselected_color=C["surface"],
        )
        self._ext_tabs.pack(fill="both", expand=True)

        self._ext_tabs.add("✓ Installiert")
        self._ext_tabs.add("◆ ComfyUI Nodes")
        self._ext_tabs.add("■ A1111 Extensions")
        self._ext_tabs.add("⭐ LoRA Manager")

        # ── Tab: Installiert ──────────────────────────────
        inst_tab = self._ext_tabs.tab("✓ Installiert")
        inst_ctrl = ctk.CTkFrame(inst_tab, fg_color=C["bg"])
        inst_ctrl.pack(fill="x", pady=(0, 8))

        self._ext_pkg_var = ctk.StringVar()
        pkg_names = ["(Paket auswaehlen)"] + [p.display_name for p in self.cfg.packages]
        self._ext_pkg_combo = ctk.CTkComboBox(
            inst_ctrl, variable=self._ext_pkg_var,
            values=pkg_names, width=220,
            fg_color=C["surface"], border_color=C["border"],
            font=("Segoe UI", 11),
            command=lambda v: self._ext_scan_installed(v),
        )
        self._ext_pkg_combo.pack(side="left")
        ctk.CTkButton(inst_ctrl, text="Scan", width=70, height=32,
                      fg_color=C["teal"], text_color=C["bg"],
                      hover_color=C["green"], font=("Segoe UI", 11, "bold"),
                      corner_radius=6,
                      command=lambda: self._ext_scan_installed(
                          self._ext_pkg_var.get())).pack(side="left", padx=6)
        ctk.CTkButton(inst_ctrl, text="Updates pruefen", width=120, height=32,
                      fg_color=C["card"], text_color=C["text"],
                      hover_color=C["surface"], font=("Segoe UI", 11),
                      corner_radius=6,
                      command=self._ext_check_updates).pack(side="left", padx=2)

        self._ext_inst_list = ctk.CTkScrollableFrame(
            inst_tab, fg_color=C["surface"], corner_radius=10)
        self._ext_inst_list.pack(fill="both", expand=True, pady=(8, 0))

        ctk.CTkLabel(self._ext_inst_list,
                     text="Paket auswaehlen und 'Scan' klicken",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            padx=16, pady=20)

        # ── Tab: ComfyUI Nodes ──────────────────────────────
        comfy_tab = self._ext_tabs.tab("◆ ComfyUI Nodes")
        comfy_ctrl = ctk.CTkFrame(comfy_tab, fg_color=C["bg"])
        comfy_ctrl.pack(fill="x", pady=(0, 8))

        # ComfyUI-Instanz auswaehlen
        comfy_pkgs = [p for p in self.cfg.packages
                      if "comfy" in p.package_name.lower()]
        comfy_vals = ["(ComfyUI auswaehlen)"] + [p.display_name for p in comfy_pkgs]
        self._ext_comfy_var = ctk.StringVar(value=comfy_vals[0])
        ctk.CTkComboBox(
            comfy_ctrl, variable=self._ext_comfy_var,
            values=comfy_vals, width=200,
            fg_color=C["surface"], border_color=C["border"],
            font=("Segoe UI", 11),
        ).pack(side="left")

        comfy_nodes_frame = ctk.CTkScrollableFrame(
            comfy_tab, fg_color=C["bg"], corner_radius=0)
        comfy_nodes_frame.pack(fill="both", expand=True, pady=(8, 0))

        # Hervorgehobene Nodes zuerst
        featured = [(k, v) for k, v in COMFYUI_NODES_CATALOG.items() if v.featured]
        others = [(k, v) for k, v in COMFYUI_NODES_CATALOG.items() if not v.featured]

        if featured:
            section_label(comfy_nodes_frame, "★ EMPFOHLENE NODES").pack(
                anchor="w", padx=4, pady=(4, 4))
            for nid, node in featured:
                self._make_ext_catalog_card(comfy_nodes_frame, node, "comfyui")

        if others:
            section_label(comfy_nodes_frame, "WEITERE NODES").pack(
                anchor="w", padx=4, pady=(10, 4))
            for nid, node in others:
                self._make_ext_catalog_card(comfy_nodes_frame, node, "comfyui")

        # ── Tab: A1111 Extensions ───────────────────────────
        a1111_tab = self._ext_tabs.tab("■ A1111 Extensions")
        a1111_ctrl = ctk.CTkFrame(a1111_tab, fg_color=C["bg"])
        a1111_ctrl.pack(fill="x", pady=(0, 8))

        # A1111/Forge Paket auswaehlen
        a1111_pkgs = [p for p in self.cfg.packages
                      if any(x in p.package_name.lower()
                             for x in ["webui", "forge", "automatic"])]
        a1111_vals = ["(WebUI auswaehlen)"] + [p.display_name for p in a1111_pkgs]
        self._ext_a1111_var = ctk.StringVar(value=a1111_vals[0])
        ctk.CTkComboBox(
            a1111_ctrl, variable=self._ext_a1111_var,
            values=a1111_vals, width=200,
            fg_color=C["surface"], border_color=C["border"],
            font=("Segoe UI", 11),
        ).pack(side="left")

        a1111_ext_frame = ctk.CTkScrollableFrame(
            a1111_tab, fg_color=C["bg"], corner_radius=0)
        a1111_ext_frame.pack(fill="both", expand=True, pady=(8, 0))

        a1111_featured = [(k, v) for k, v in A1111_EXTENSIONS_CATALOG.items()
                          if v.featured]
        a1111_others = [(k, v) for k, v in A1111_EXTENSIONS_CATALOG.items()
                        if not v.featured]

        if a1111_featured:
            section_label(a1111_ext_frame, "★ EMPFOHLENE EXTENSIONS").pack(
                anchor="w", padx=4, pady=(4, 4))
            for eid, ext in a1111_featured:
                self._make_ext_catalog_card(a1111_ext_frame, ext, "a1111")

        if a1111_others:
            section_label(a1111_ext_frame, "WEITERE EXTENSIONS").pack(
                anchor="w", padx=4, pady=(10, 4))
            for eid, ext in a1111_others:
                self._make_ext_catalog_card(a1111_ext_frame, ext, "a1111")

        # ── Tab: LoRA Manager (ComfyUI-Lora-Manager) ───────
        lora_tab = self._ext_tabs.tab("⭐ LoRA Manager")
        self._build_lora_manager_tab(lora_tab)

        return f

    def _make_ext_catalog_card(self, parent, ext_def: "ExtensionDef", ext_type: str):
        card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=10)
        card.pack(fill="x", padx=4, pady=3)

        # Featured Star
        if ext_def.featured:
            ctk.CTkLabel(card, text="⭐", font=("Segoe UI", 14),
                         text_color=C["yellow"], width=28).pack(
                side="left", padx=(8, 0))
        else:
            ctk.CTkLabel(card, text="  ", width=28).pack(side="left")

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)

        ctk.CTkLabel(info, text=ext_def.display_name,
                     font=("Segoe UI", 12, "bold"),
                     text_color=C["lavender"] if ext_type == "comfyui" else C["peach"],
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=ext_def.description[:100],
                     font=("Segoe UI", 10), text_color=C["subtext"],
                     anchor="w", wraplength=450, justify="left").pack(
            anchor="w")

        if ext_def.github_repo:
            ctk.CTkLabel(info, text=f"github.com/{ext_def.github_repo}",
                         font=("Cascadia Code", 9), text_color=C["border"],
                         anchor="w").pack(anchor="w")

        btn_f = ctk.CTkFrame(card, fg_color="transparent")
        btn_f.pack(side="right", padx=8)

        if ext_def.homepage:
            ctk.CTkButton(btn_f, text="⎋ GitHub", width=70, height=26,
                          fg_color=C["surface"], text_color=C["subtext"],
                          hover_color=C["border"], font=("Segoe UI", 9),
                          corner_radius=6,
                          command=lambda u=ext_def.homepage: webbrowser.open(u)
                          ).pack(pady=1)

        ctk.CTkButton(
            btn_f, text="⬇ Installieren", width=100, height=30,
            fg_color=C["mauve"] if ext_def.featured else C["card"],
            text_color=C["bg"] if ext_def.featured else C["text"],
            hover_color=C["lavender"], font=("Segoe UI", 10, "bold"),
            corner_radius=6,
            command=lambda e=ext_def, t=ext_type: self._ext_install(e, t),
        ).pack(pady=1)

    def _ext_install(self, ext_def: "ExtensionDef", ext_type: str):
        """Installiert eine Extension in das ausgewaehlte Paket."""
        # Ziel-Paket ermitteln
        if ext_type == "comfyui":
            pkg_name = self._ext_comfy_var.get()
        else:
            pkg_name = self._ext_a1111_var.get()

        pkg = next((p for p in self.cfg.packages
                    if p.display_name == pkg_name), None)

        if not pkg:
            self._toast_show("Kein Ziel-Paket ausgewaehlt!", C["yellow"])
            return

        ok = messagebox.askyesno(
            "Extension installieren",
            f"'{ext_def.display_name}' installieren in:\n{pkg.abs_path}\n\n"
            f"Quelle: github.com/{ext_def.github_repo}\n\n"
            + (f"Hinweis: {ext_def.install_notes}\n" if ext_def.install_notes else "")
        )
        if not ok:
            return

        def progress_cb(step: str, pct: float, msg: str):
            self.after(0, lambda: self._toast_show(
                f"[{step}] {msg[:50]}", C["teal"], ms=2000))

        def done_cb(success: bool, msg: str):
            def _do():
                if success:
                    self._toast_show(
                        f"{ext_def.display_name} installiert!", C["green"])
                    self._log(
                        f"[Extension] {ext_def.display_name} in {pkg.display_name}\n",
                        C["green"])
                    if ext_def.install_notes:
                        self._log(f"  Hinweis: {ext_def.install_notes}\n", C["yellow"])
                else:
                    self._toast_show(f"Fehler: {msg[:50]}", C["red"])
                    self._log(f"[Extension Fehler] {msg}\n", C["red"])
            self.after(0, _do)

        if ext_type == "comfyui":
            self._ext_manager.install_comfyui_node(
                ext_def, pkg.abs_path, progress_cb, done_cb)
        else:
            self._ext_manager.install_a1111_extension(
                ext_def, pkg.abs_path, progress_cb, done_cb)

    def _ext_scan_installed(self, pkg_display_name: str):
        """Scannt installierte Extensions eines Paketes."""
        pkg = next((p for p in self.cfg.packages
                    if p.display_name == pkg_display_name), None)
        if not pkg:
            return

        for w in self._ext_inst_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._ext_inst_list, text="Scanne...",
                     font=("Segoe UI", 12), text_color=C["yellow"]).pack(
            padx=16, pady=12)

        def worker():
            is_comfyui = "comfyui" in pkg.package_name.lower()
            if is_comfyui:
                exts = self._ext_manager.scan_comfyui_nodes(pkg.abs_path)
            else:
                exts = self._ext_manager.scan_a1111_extensions(pkg.abs_path)

            def show():
                for w in self._ext_inst_list.winfo_children():
                    w.destroy()
                if not exts:
                    ctk.CTkLabel(self._ext_inst_list,
                                 text=f"Keine Extensions in {pkg.display_name}",
                                 font=("Segoe UI", 12),
                                 text_color=C["subtext"]).pack(padx=16, pady=20)
                    return

                ctk.CTkLabel(self._ext_inst_list,
                             text=f"{len(exts)} Extensions in {pkg.display_name}",
                             font=("Segoe UI", 12, "bold"),
                             text_color=C["text"]).pack(
                    anchor="w", padx=8, pady=(4, 8))

                for ext in exts:
                    self._make_installed_ext_card(
                        self._ext_inst_list, ext, is_comfyui)
            self.after(0, show)

        threading.Thread(target=worker, daemon=True).start()

    def _make_installed_ext_card(self, parent, ext: "InstalledExtension",
                                  is_comfyui: bool):
        card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=8)
        card.pack(fill="x", padx=4, pady=2)

        dot_color = C["green"] if ext.is_enabled else C["subtext"]
        ctk.CTkLabel(card, text="●", text_color=dot_color,
                     font=("Segoe UI", 12), width=22).pack(
            side="left", padx=(8, 4))

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=5)
        ctk.CTkLabel(info, text=ext.ext_def.display_name,
                     font=("Segoe UI", 11, "bold"),
                     text_color=C["text"] if ext.is_enabled else C["subtext"],
                     anchor="w").pack(anchor="w")
        sha_txt = ext.installed_sha[:8] if ext.installed_sha else "unbekannt"
        update_txt = "  🔔 Update verfuegbar!" if ext.update_available else ""
        ctk.CTkLabel(info, text=f"SHA: {sha_txt}{update_txt}",
                     font=("Segoe UI", 9), text_color=C["subtext"],
                     anchor="w").pack(anchor="w")

        btn_f = ctk.CTkFrame(card, fg_color="transparent")
        btn_f.pack(side="right", padx=6)

        if ext.update_available:
            ctk.CTkButton(btn_f, text="⟳ Update", width=70, height=24,
                          fg_color=C["teal"], text_color=C["bg"],
                          hover_color=C["green"], font=("Segoe UI", 9, "bold"),
                          corner_radius=5,
                          command=lambda e=ext: self._ext_do_update(e)
                          ).pack(side="left", padx=2)

        if is_comfyui:
            toggle_txt = "⏸ Deaktiv." if ext.is_enabled else "▶ Aktivieren"
            ctk.CTkButton(btn_f, text=toggle_txt, width=85, height=24,
                          fg_color=C["card"], text_color=C["text"],
                          hover_color=C["surface"], font=("Segoe UI", 9),
                          corner_radius=5,
                          command=lambda e=ext: self._ext_toggle(e)
                          ).pack(side="left", padx=2)

        ctk.CTkButton(btn_f, text="🗑 Remove", width=70, height=24,
                      fg_color=C["surface"], text_color=C["red"],
                      hover_color=C["card"], font=("Segoe UI", 9),
                      corner_radius=5,
                      command=lambda e=ext: self._ext_remove(e)
                      ).pack(side="left", padx=2)

    def _ext_toggle(self, ext: "InstalledExtension"):
        ok = self._ext_manager.toggle_extension(ext)
        if ok:
            state = "aktiviert" if ext.is_enabled else "deaktiviert"
            self._toast_show(f"{ext.ext_def.display_name} {state}", C["teal"])
        self._ext_scan_installed(self._ext_pkg_var.get())

    def _ext_remove(self, ext: "InstalledExtension"):
        if messagebox.askyesno(
            "Extension entfernen",
            f"'{ext.ext_def.display_name}' wirklich loeschen?\n{ext.install_path}"
        ):
            ok = self._ext_manager.uninstall_extension(ext)
            if ok:
                self._toast_show(f"{ext.ext_def.display_name} entfernt", C["yellow"])
            else:
                self._toast_show("Loeschen fehlgeschlagen", C["red"])
            self._ext_scan_installed(self._ext_pkg_var.get())

    def _ext_do_update(self, ext: "InstalledExtension"):
        def progress_cb(step, pct, msg):
            self.after(0, lambda: self._toast_show(
                f"[{step}] {msg[:40]}", C["teal"], ms=1500))
        def done_cb(ok, msg):
            def _do():
                if ok:
                    self._toast_show(f"{ext.ext_def.display_name} aktualisiert!", C["green"])
                    ext.update_available = False
                else:
                    self._toast_show(f"Update fehlgeschlagen: {msg[:30]}", C["red"])
            self.after(0, _do)
        self._ext_manager.update_extension(ext, progress_cb, done_cb)

    def _ext_check_updates(self):
        pkg_name = self._ext_pkg_var.get()
        pkg = next((p for p in self.cfg.packages
                    if p.display_name == pkg_name), None)
        if not pkg:
            self._toast_show("Kein Paket ausgewaehlt", C["yellow"])
            return
        self._toast_show("Pruefe Updates...", C["teal"])

        def worker():
            is_comfyui = "comfyui" in pkg.package_name.lower()
            if is_comfyui:
                exts = self._ext_manager.scan_comfyui_nodes(pkg.abs_path)
            else:
                exts = self._ext_manager.scan_a1111_extensions(pkg.abs_path)
            exts = self._ext_manager.check_updates(exts)
            updates = sum(1 for e in exts if e.update_available)
            self.after(0, lambda: self._toast_show(
                f"{updates} Updates verfuegbar", C["teal"] if updates else C["green"]))
            self.after(0, lambda: self._show_ext_list(exts, is_comfyui))

        threading.Thread(target=worker, daemon=True).start()

    def _show_ext_list(self, exts: list, is_comfyui: bool):
        for w in self._ext_inst_list.winfo_children():
            w.destroy()
        for ext in exts:
            self._make_installed_ext_card(self._ext_inst_list, ext, is_comfyui)

    def _build_lora_manager_tab(self, parent):
        """Spezieller Tab fuer ComfyUI-Lora-Manager."""
        # Info-Karte
        info_card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=12)
        info_card.pack(fill="x", pady=(0, 16))

        hdr_row = ctk.CTkFrame(info_card, fg_color="transparent")
        hdr_row.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(hdr_row, text="⭐  ComfyUI LoRA Manager",
                     font=("Segoe UI", 16, "bold"),
                     text_color=C["yellow"]).pack(side="left")
        ctk.CTkLabel(hdr_row, text="von willmiao",
                     font=("Segoe UI", 11), text_color=C["subtext"]).pack(
            side="left", padx=8)

        ctk.CTkLabel(info_card, text=(
            "Vollstaendiger LoRA-Manager fuer ComfyUI:\n"
            "• Vorschau-Thumbnails aus CivitAI automatisch laden\n"
            "• Aktivierungs-Tags anzeigen und kopieren\n"
            "• LoRAs nach Ordnern browsen und suchen\n"
            "• CivitAI-Metadaten synchronisieren\n"
            "• Top-Picks Sidebar fuer schnellen Zugriff"
        ), font=("Segoe UI", 11), text_color=C["text"],
                     justify="left").pack(anchor="w", padx=16, pady=(4, 0))

        ctk.CTkLabel(info_card,
                     text="github.com/willmiao/ComfyUI-Lora-Manager",
                     font=("Cascadia Code", 10), text_color=C["blue"]).pack(
            anchor="w", padx=16, pady=(4, 8))

        btn_row = ctk.CTkFrame(info_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(btn_row, text="⎋ GitHub oeffnen", width=140, height=34,
                      fg_color=C["surface"], text_color=C["blue"],
                      hover_color=C["card"], font=("Segoe UI", 11),
                      corner_radius=8,
                      command=lambda: webbrowser.open(
                          "https://github.com/willmiao/ComfyUI-Lora-Manager")
                      ).pack(side="left", padx=(0, 8))

        # Ziel-ComfyUI auswaehlen
        comfy_pkgs = [p for p in self.cfg.packages
                      if "comfyui" in p.package_name.lower()]
        if comfy_pkgs:
            self._lm_pkg_var = ctk.StringVar(value=comfy_pkgs[0].display_name)
            ctk.CTkComboBox(
                btn_row, variable=self._lm_pkg_var,
                values=[p.display_name for p in comfy_pkgs],
                width=200, fg_color=C["surface"],
                border_color=C["border"], font=("Segoe UI", 11),
            ).pack(side="left", padx=(0, 8))
            ctk.CTkButton(
                btn_row, text="⬇ Installieren", width=120, height=34,
                fg_color=C["yellow"], text_color=C["bg"],
                hover_color=C["peach"], font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                command=self._install_lora_manager,
            ).pack(side="left")
        else:
            ctk.CTkLabel(btn_row,
                         text="Kein ComfyUI installiert!",
                         font=("Segoe UI", 11), text_color=C["red"]).pack(side="left")

        # Status-Check
        status_frame = ctk.CTkFrame(parent, fg_color=C["surface"], corner_radius=10)
        status_frame.pack(fill="x", pady=(0, 12))
        section_label(status_frame, "INSTALLATIONS-STATUS").pack(
            anchor="w", padx=12, pady=(8, 4))

        self._lm_status_label = ctk.CTkLabel(
            status_frame, text="", font=("Segoe UI", 11),
            text_color=C["subtext"])
        self._lm_status_label.pack(anchor="w", padx=12, pady=(0, 8))

        # Pruefen ob schon installiert
        self._check_lora_manager_status()

        # LoRA-Ordner-Uebersicht
        section_label(parent, "LORA ORDNER-UEBERSICHT").pack(
            anchor="w", pady=(8, 4))
        self._lm_folders_frame = ctk.CTkScrollableFrame(
            parent, fg_color=C["surface"], corner_radius=10, height=180)
        self._lm_folders_frame.pack(fill="x")
        self._refresh_lora_folders()

    def _install_lora_manager(self):
        if not HAS_EXT:
            return
        pkg_name = getattr(self, "_lm_pkg_var", None)
        pkg_display = pkg_name.get() if pkg_name else ""
        pkg = next((p for p in self.cfg.packages
                    if p.display_name == pkg_display), None)
        if not pkg:
            self._toast_show("Kein ComfyUI-Paket gefunden", C["yellow"])
            return

        from extensions import COMFYUI_NODES_CATALOG
        lora_mgr = COMFYUI_NODES_CATALOG.get("ComfyUI-Lora-Manager")
        if not lora_mgr:
            return

        ok = messagebox.askyesno(
            "ComfyUI LoRA Manager installieren",
            f"Installiere ComfyUI-Lora-Manager in:\n{pkg.abs_path}\n\n"
            f"Quelle: github.com/{lora_mgr.github_repo}\n\n"
            f"Hinweis: {lora_mgr.install_notes}"
        )
        if not ok:
            return

        def progress_cb(step, pct, msg):
            self.after(0, lambda: self._toast_show(
                f"[{step}] {msg[:50]}", C["teal"], ms=2000))

        def done_cb(success, msg):
            def _do():
                if success:
                    self._toast_show(
                        "ComfyUI LoRA Manager installiert! ComfyUI neu starten.",
                        C["yellow"], ms=8000)
                    self._log("[LoRA Manager] Installiert! ComfyUI neu starten.\n",
                              C["yellow"])
                    self._check_lora_manager_status()
                else:
                    self._toast_show(f"Fehler: {msg[:50]}", C["red"])
                    self._log(f"[LoRA Manager Fehler] {msg}\n", C["red"])
            self.after(0, _do)

        self._ext_manager.install_comfyui_node(lora_mgr, pkg.abs_path,
                                                 progress_cb, done_cb)

    def _check_lora_manager_status(self):
        """Prueft ob ComfyUI-Lora-Manager installiert ist."""
        comfy_pkgs = [p for p in self.cfg.packages
                      if "comfyui" in p.package_name.lower()]
        statuses = []
        for pkg in comfy_pkgs:
            lm_path = pkg.abs_path / "custom_nodes" / "ComfyUI-Lora-Manager"
            if lm_path.exists():
                statuses.append(f"✓ {pkg.display_name}: Installiert ({lm_path.name})")
            else:
                statuses.append(f"✗ {pkg.display_name}: Nicht installiert")

        if hasattr(self, "_lm_status_label"):
            txt = "\n".join(statuses) if statuses else "Kein ComfyUI gefunden"
            color = C["green"] if any("✓" in s for s in statuses) else C["subtext"]
            self._lm_status_label.configure(text=txt, text_color=color)

    def _refresh_lora_folders(self):
        if not hasattr(self, "_lm_folders_frame"):
            return
        for w in self._lm_folders_frame.winfo_children():
            w.destroy()

        lora_root = self.cfg.models_root / "Lora"
        if not lora_root.exists():
            ctk.CTkLabel(self._lm_folders_frame,
                         text=f"LoRA-Ordner nicht gefunden: {lora_root}",
                         font=("Segoe UI", 11), text_color=C["yellow"]).pack(
                padx=12, pady=8)
            return

        try:
            entries = sorted(lora_root.rglob("*.safetensors"))
            folders: dict[str, int] = {}
            for f in entries:
                rel = str(f.parent.relative_to(lora_root))
                folders[rel] = folders.get(rel, 0) + 1

            if not folders:
                ctk.CTkLabel(self._lm_folders_frame,
                             text="Keine LoRA-Dateien gefunden",
                             font=("Segoe UI", 11),
                             text_color=C["subtext"]).pack(padx=12, pady=8)
                return

            total = sum(folders.values())
            ctk.CTkLabel(self._lm_folders_frame,
                         text=f"Gesamt: {total} LoRA-Dateien",
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["text"]).pack(anchor="w", padx=12, pady=(6, 4))

            for folder, count in sorted(folders.items(), key=lambda x: -x[1]):
                row = ctk.CTkFrame(self._lm_folders_frame, fg_color=C["card"],
                                   corner_radius=6)
                row.pack(fill="x", padx=6, pady=1)
                ctk.CTkLabel(row, text=folder or "(root)",
                             font=("Cascadia Code", 10), text_color=C["lavender"],
                             anchor="w").pack(side="left", padx=8, pady=3)
                ctk.CTkLabel(row, text=f"{count} LoRAs",
                             font=("Segoe UI", 10), text_color=C["subtext"]).pack(
                    side="right", padx=8)
        except Exception as e:
            ctk.CTkLabel(self._lm_folders_frame, text=f"Fehler: {e}",
                         font=("Segoe UI", 10), text_color=C["red"]).pack(
                padx=12, pady=4)

    # ─── Beenden ────────────────────────────────────────────

    def _on_close(self):
        running = self.launcher.get_running_ids()
        if running:
            names = []
            for rid in running:
                pkg = next((p for p in self.cfg.packages if p.id == rid), None)
                if pkg:
                    names.append(pkg.display_name)
            if messagebox.askyesno(
                "Beenden",
                f"Noch laufende Pakete:\n{', '.join(names)}\n\nAlle stoppen und beenden?"
            ):
                self.launcher.stop_all()
                self.destroy()
        else:
            self.destroy()


# ─────────────────────────── Start ───────────────────────────

if __name__ == "__main__":
    app = PyMatrixApp()
    app.mainloop()
