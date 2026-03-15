"""
SD Model Manager v2.0
Verwaltet Symlinks/Junctions, Downloads, Disk-Scanning
fuer Stable Diffusion WebUI Pakete.
"""

import json
import os
import sys
import shutil
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# Eigene Module
try:
    from downloader import (CivitAIClient, HuggingFaceClient, DownloadManager,
                            DownloadTask, ModelInfo, detect_source, fmt_size, fmt_speed,
                            CIVITAI_TYPE_MAP)
    HAS_DOWNLOADER = True
except ImportError:
    HAS_DOWNLOADER = False

try:
    from scanner import (scan_folder_sizes, find_duplicates, find_orphans,
                         FolderStats, DuplicateGroup, OrphanFile,
                         fmt_size as scan_fmt_size)
    HAS_SCANNER = True
except ImportError:
    HAS_SCANNER = False

# ─────────────────────────── Pfade ───────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
PROFILES_DIR = BASE_DIR / "profiles"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
MASTER_TYPES_FILE = CONFIG_DIR / "master_types.json"

VERSION = "2.0"

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
    "flamingo": "#f2cdcd",
}

# ─────────────────────────── Daten ───────────────────────────

master_root: str = ""
packages_root: str = ""
civitai_api_key: str = ""
master_types: dict = {}
profiles: dict = {}


def load_settings() -> None:
    global master_root, packages_root, civitai_api_key
    defaults = {
        "master_root":   "D:\\Programme\\stability_matrix\\models",
        "packages_root": "D:\\Programme\\stability_matrix\\Packages",
        "civitai_api_key": "",
    }
    if SETTINGS_FILE.exists():
        try:
            d = json.loads(SETTINGS_FILE.read_text("utf-8"))
            defaults.update(d)
        except Exception:
            pass
    master_root     = defaults["master_root"]
    packages_root   = defaults["packages_root"]
    civitai_api_key = defaults.get("civitai_api_key", "")


def save_settings() -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps({
            "master_root": master_root,
            "packages_root": packages_root,
            "civitai_api_key": civitai_api_key,
        }, indent=2, ensure_ascii=False), "utf-8",
    )


def load_master_types() -> None:
    global master_types
    if MASTER_TYPES_FILE.exists():
        data = json.loads(MASTER_TYPES_FILE.read_text("utf-8"))
        master_types = data["types"]
    else:
        master_types = {}


def load_profiles() -> None:
    global profiles
    profiles = {}
    if PROFILES_DIR.exists():
        for f in sorted(PROFILES_DIR.glob("*.json")):
            try:
                d = json.loads(f.read_text("utf-8"))
                profiles[f.stem] = d
            except Exception as e:
                print(f"[WARN] {f.name}: {e}")


def reload_all() -> None:
    load_settings()
    load_master_types()
    load_profiles()


def master_folder(type_key: str) -> Path:
    if type_key not in master_types:
        return Path(master_root) / type_key
    return Path(master_root) / master_types[type_key]["folder"]


# ─────────────────────────── Link-Logik ──────────────────────

def is_link(path: Path) -> bool:
    try:
        return path.is_symlink() or (
            sys.platform == "win32"
            and path.exists()
            and bool(path.stat().st_file_attributes & 0x400)
        )
    except Exception:
        return path.is_symlink()


def _rmlink(path: Path) -> None:
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "rmdir", str(path)], capture_output=True)
    else:
        path.unlink(missing_ok=True)


def create_link(source: Path, dest: Path, dry_run: bool) -> tuple[str, str]:
    source.mkdir(parents=True, exist_ok=True) if not dry_run else None

    if dest.exists() or dest.is_symlink():
        if is_link(dest):
            try:
                target = Path(os.readlink(str(dest)))
                if target == source:
                    return "skip", f"Bereits verknuepft: {dest.name}"
            except Exception:
                pass
            if not dry_run:
                _rmlink(dest)
        else:
            items = list(dest.iterdir()) if dest.is_dir() else []
            if items and not dry_run:
                for item in items:
                    tgt = source / item.name
                    if not tgt.exists():
                        shutil.move(str(item), str(tgt))
            if not dry_run:
                if dest.is_dir():
                    shutil.rmtree(str(dest), ignore_errors=True)
                else:
                    dest.unlink(missing_ok=True)

    if dry_run:
        return "dry", f"[Vorschau] {dest.name} -> {source.name}"

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            r = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(dest), str(source)],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                os.symlink(str(source), str(dest))
        else:
            os.symlink(str(source), str(dest))
        return "ok", f"Verknuepft: {dest.name} -> {source.name}"
    except Exception as e:
        return "error", f"Fehler: {dest.name}: {e}"


def apply_profile(profile: dict, dry_run: bool) -> list[tuple[str, str]]:
    results = []
    pkg_dir = Path(packages_root) / profile["package_folder"]

    if not pkg_dir.exists() and not dry_run:
        return [("warn", f"Paketordner nicht gefunden: {pkg_dir}")]

    for rule in profile.get("rules", []):
        src_types = rule["source_types"]
        target_rel = rule["target"]
        dest = pkg_dir / target_rel

        if len(src_types) == 1:
            src = master_folder(src_types[0])
            status, msg = create_link(src, dest, dry_run)
            results.append((status, msg))
        else:
            if not dry_run:
                dest.mkdir(parents=True, exist_ok=True)
            for t in src_types:
                src = master_folder(t)
                sub = dest / master_types.get(t, {}).get("folder", t)
                status, msg = create_link(src, sub, dry_run)
                results.append((status, f"{target_rel}/{src.name}: {msg}"))

    return results


# ─────────────────────────── Hilfs-Widgets ───────────────────

def badge(parent, text: str, color: str, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, width=10,
        fg_color=color, text_color=C["bg"],
        corner_radius=4, font=("Segoe UI", 10, "bold"),
        **kwargs,
    )


def section_label(parent, text: str) -> ctk.CTkLabel:
    lbl = ctk.CTkLabel(
        parent, text=text,
        font=("Segoe UI", 11, "bold"),
        text_color=C["subtext"],
    )
    return lbl


def stat_card(parent, value: str, label: str, color: str) -> ctk.CTkFrame:
    card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=10)
    ctk.CTkLabel(card, text=value, font=("Segoe UI", 28, "bold"),
                 text_color=color).pack(pady=(12, 0))
    ctk.CTkLabel(card, text=label, font=("Segoe UI", 10),
                 text_color=C["subtext"]).pack(pady=(0, 12))
    return card


# ─────────────────────────── Hauptanwendung ──────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        reload_all()

        self.title("SD Model Manager v2.0")
        self.geometry("1280x860")
        self.configure(fg_color=C["bg"])
        self.minsize(960, 640)

        self._log_lines: list[tuple[str, str]] = []
        self._active_idx = -1
        self._active_page = None
        self._download_mgr = None
        if HAS_DOWNLOADER:
            self._download_mgr = DownloadManager(max_concurrent=2)
            self._download_mgr.on_progress = self._on_download_progress
            self._download_mgr.on_complete = self._on_download_complete

        self._build_ui()
        self.refresh_all()

    # ── UI-Aufbau ──────────────────────────────────────────────

    def _build_ui(self):
        # Statusleiste (unten)
        self.statusbar = ctk.CTkFrame(self, height=30, fg_color=C["surface"],
                                       corner_radius=0)
        self.statusbar.pack(side="bottom", fill="x")
        self.statusbar.pack_propagate(False)

        self._status_left = ctk.CTkLabel(
            self.statusbar, text="", font=("Segoe UI", 10),
            text_color=C["subtext"], anchor="w")
        self._status_left.pack(side="left", padx=12)

        self._status_right = ctk.CTkLabel(
            self.statusbar, text=f"v{VERSION}", font=("Segoe UI", 10),
            text_color=C["subtext"], anchor="e")
        self._status_right.pack(side="right", padx=12)

        # Seitenleiste
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=C["surface"],
                                     corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 4))
        ctk.CTkLabel(
            logo_frame, text="SD Model", font=("Segoe UI", 20, "bold"),
            text_color=C["mauve"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text="Manager", font=("Segoe UI", 20, "bold"),
            text_color=C["lavender"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            self.sidebar, text=f"v{VERSION} \u2022 StabilityMatrix",
            font=("Segoe UI", 10), text_color=C["subtext"],
        ).pack(anchor="w", padx=16, pady=(0, 16))

        # Trennlinie
        ctk.CTkFrame(self.sidebar, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=(0, 8))

        # Navigation
        self._nav_buttons: list[ctk.CTkButton] = []
        self._nav_pages = []
        nav_items = [
            ("\u25A0  Dashboard",    0),
            ("\u25B6  Profile",      1),
            ("\u25BC  Downloader",   2),
            ("\u25C6  Scanner",      3),
            ("\u2261  Master-Typen", 4),
            ("\u2699  Einstellungen",5),
        ]
        for label, idx in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                fg_color="transparent", hover_color=C["card"],
                text_color=C["text"], font=("Segoe UI", 13),
                corner_radius=8, height=40,
                command=lambda i=idx: self._navigate(i),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_buttons.append(btn)

        # Untere Sidebar-Buttons
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=8, pady=8)

        ctk.CTkButton(
            bottom, text="\u21BB  Neu laden", anchor="w",
            fg_color="transparent", hover_color=C["card"],
            text_color=C["subtext"], font=("Segoe UI", 12),
            corner_radius=6, height=34,
            command=lambda: [reload_all(), self.refresh_all()],
        ).pack(fill="x", pady=1)

        ctk.CTkButton(
            bottom, text="\u2630  Log", anchor="w",
            fg_color="transparent", hover_color=C["card"],
            text_color=C["subtext"], font=("Segoe UI", 12),
            corner_radius=6, height=34,
            command=lambda: self._navigate(6),
        ).pack(fill="x", pady=1)

        # Hauptbereich
        self.main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        # Toast-Container (ueberlagert oben rechts)
        self._toast_label = ctk.CTkLabel(
            self.main, text="", font=("Segoe UI", 11, "bold"),
            text_color=C["bg"], fg_color=C["green"],
            corner_radius=8, height=0, width=0,
        )

        # Seiten bauen
        self.page_dashboard  = self._build_dashboard()
        self.page_profiles   = self._build_profiles()
        self.page_downloader = self._build_downloader()
        self.page_scanner    = self._build_scanner()
        self.page_types      = self._build_types()
        self.page_settings   = self._build_settings()
        self.page_log        = self._build_log()

        self._pages = [
            self.page_dashboard, self.page_profiles,
            self.page_downloader, self.page_scanner,
            self.page_types, self.page_settings,
            self.page_log,
        ]
        self._active_page = None
        self._active_idx = -1
        self._navigate(0)
        self._update_statusbar()

    def _navigate(self, idx: int):
        page = self._pages[idx]
        if self._active_page:
            self._active_page.pack_forget()
        page.pack(fill="both", expand=True, padx=20, pady=16)
        self._active_page = page
        self._active_idx = idx

        # Sidebar-Highlighting
        for i, btn in enumerate(self._nav_buttons):
            if i == idx:
                btn.configure(fg_color=C["card"], text_color=C["mauve"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text"])

        # Refresh
        refresh_map = {
            0: self._refresh_dashboard,
            1: self._refresh_profiles,
            3: lambda: None,  # Scanner scannt on-demand
            4: self._refresh_types,
        }
        if idx in refresh_map:
            refresh_map[idx]()

    def _show_toast(self, message: str, color: str = None, duration: int = 3000):
        color = color or C["green"]
        self._toast_label.configure(text=f"  {message}  ", fg_color=color,
                                     text_color=C["bg"], height=32)
        self._toast_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        self.after(duration, lambda: self._toast_label.place_forget())

    def _update_statusbar(self):
        mr_ok = Path(master_root).exists() if master_root else False
        enabled = sum(1 for p in profiles.values() if p.get("enabled"))
        dot = "\u25CF" if mr_ok else "\u25CB"
        color_txt = "OK" if mr_ok else "FEHLT"
        self._status_left.configure(
            text=f"{dot} Master-Root: {color_txt}  |  {enabled} Profile aktiv  |  "
                 f"{len(master_types)} Typen",
            text_color=C["green"] if mr_ok else C["red"],
        )

    # ── Dashboard ─────────────────────────────────────────────

    def _build_dashboard(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        # Header
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(hdr, text="Dashboard",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(hdr, text=datetime.now().strftime("%d.%m.%Y"),
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            side="right", padx=8)

        # Stat-Karten
        self._dash_cards = ctk.CTkFrame(f, fg_color=C["bg"])
        self._dash_cards.pack(fill="x", pady=(0, 20))

        # Schnellstart-Panel
        section_label(f, "SCHNELLSTART").pack(anchor="w", pady=(0, 6))
        qa = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        qa.pack(fill="x", pady=(0, 16))

        top_row = ctk.CTkFrame(qa, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 4))

        self._dry_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            top_row, text="Dry-Run (nur Vorschau)", variable=self._dry_var,
            font=("Segoe UI", 12), text_color=C["text"],
            button_color=C["blue"], button_hover_color=C["sky"],
            progress_color=C["surface"],
        ).pack(side="left")

        btn_row = ctk.CTkFrame(qa, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 12))

        self._dash_profile_var = ctk.StringVar()
        self._dash_profile_combo = ctk.CTkComboBox(
            btn_row, variable=self._dash_profile_var,
            font=("Segoe UI", 12), width=220,
            fg_color=C["surface"], border_color=C["border"],
            button_color=C["border"], dropdown_fg_color=C["card"],
        )
        self._dash_profile_combo.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="\u25B6  Profil anwenden",
            font=("Segoe UI", 12, "bold"), height=38, corner_radius=8,
            fg_color=C["blue"], text_color=C["bg"],
            hover_color=C["sky"],
            command=self._apply_selected_from_dash,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="\u25B6\u25B6  Alle aktiven Profile",
            font=("Segoe UI", 12, "bold"), height=38, corner_radius=8,
            fg_color=C["mauve"], text_color=C["bg"],
            hover_color=C["lavender"],
            command=self._apply_all,
        ).pack(side="left")

        # Letzter Log
        section_label(f, "LETZTE AUSFUEHRUNG").pack(anchor="w", pady=(0, 6))
        self._dash_log = ctk.CTkTextbox(
            f, height=160, font=("Cascadia Code", 10),
            fg_color=C["card"], text_color=C["text"],
            corner_radius=10, state="disabled",
        )
        self._dash_log.pack(fill="both", expand=True)
        return f

    def _refresh_dashboard(self):
        for w in self._dash_cards.winfo_children():
            w.destroy()

        enabled_count = sum(1 for p in profiles.values() if p.get("enabled"))
        found_count = sum(
            1 for p in profiles.values()
            if (Path(packages_root) / p["package_folder"]).exists()
        )
        master_exists = Path(master_root).exists()
        types_ok = sum(1 for k in master_types if master_folder(k).exists())

        # Download-Zaehler
        dl_active = 0
        if self._download_mgr:
            dl_active = sum(1 for t in self._download_mgr.tasks
                           if t.status == "downloading")

        stats = [
            ("Profile aktiv", str(enabled_count), C["green"]),
            ("Pakete gefunden", str(found_count), C["blue"]),
            ("Typen vorhanden", f"{types_ok}/{len(master_types)}", C["teal"]),
            ("Master-Root", "OK" if master_exists else "FEHLT",
             C["green"] if master_exists else C["red"]),
            ("Downloads", str(dl_active), C["peach"]),
        ]
        for title, val, color in stats:
            card = stat_card(self._dash_cards, val, title, color)
            card.pack(side="left", expand=True, fill="both", padx=4)

        keys = sorted(p for p, d in profiles.items() if d.get("enabled"))
        self._dash_profile_combo.configure(values=keys)
        if keys and not self._dash_profile_var.get():
            self._dash_profile_var.set(keys[0])

        self._update_statusbar()

    def _apply_all(self):
        ps = [d for d in profiles.values() if d.get("enabled")]
        self._run_apply(ps, self._dry_var.get())

    def _apply_selected_from_dash(self):
        key = self._dash_profile_var.get()
        if key and key in profiles:
            self._run_apply([profiles[key]], self._dry_var.get())

    def _run_apply(self, profile_list: list, dry: bool):
        self._navigate(6)  # Log-Seite
        self._log_clear()
        self._log(f"{'='*60}\n", C["border"])
        self._log(f"  Start: {datetime.now().strftime('%H:%M:%S')}  |  "
                  f"Dry-Run: {'JA' if dry else 'NEIN'}\n", C["subtext"])
        self._log(f"{'='*60}\n\n", C["border"])

        def worker():
            ok = skip = warn = err = 0
            for prof in profile_list:
                name = prof.get("display_name", prof.get("name", "?"))
                self._log(f"\u25B6  {name}\n", C["mauve"])
                results = apply_profile(prof, dry)
                for status, msg in results:
                    sym, col = {
                        "ok":    ("\u2713", C["green"]),
                        "skip":  ("\u2500", C["subtext"]),
                        "warn":  ("!", C["yellow"]),
                        "error": ("\u2717", C["red"]),
                        "dry":   ("~", C["teal"]),
                    }.get(status, ("?", C["text"]))
                    self._log(f"   {sym}  {msg}\n", col)
                    if status == "ok":    ok += 1
                    elif status == "skip":skip += 1
                    elif status == "warn":warn += 1
                    elif status == "error":err += 1
                self._log("\n")

            self._log(f"{'='*60}\n", C["border"])
            self._log(
                f"  \u2713 {ok}  \u2500 {skip}  ! {warn}  \u2717 {err}\n",
                C["green"] if not err else C["red"],
            )
            self._log(f"{'='*60}\n", C["border"])
            self.after(100, self._refresh_dashboard)
            if not err:
                self.after(200, lambda: self._show_toast(
                    f"Fertig: {ok} verknuepft, {skip} uebersprungen"))

        threading.Thread(target=worker, daemon=True).start()

    # ── Profile ───────────────────────────────────────────────

    def _build_profiles(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(hdr, text="WebUI Profile",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkButton(
            hdr, text="+ Neues Profil",
            fg_color=C["green"], text_color=C["bg"],
            hover_color=C["teal"], font=("Segoe UI", 12, "bold"),
            height=36, corner_radius=8,
            command=self._new_profile,
        ).pack(side="right")

        body = ctk.CTkFrame(f, fg_color=C["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # Linke Spalte: Profil-Liste
        left = ctk.CTkFrame(body, fg_color=C["surface"], corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        section_label(left, "PROFILE").pack(anchor="w", padx=12, pady=(10, 6))
        self._profile_list_frame = ctk.CTkScrollableFrame(
            left, fg_color=C["surface"], corner_radius=0)
        self._profile_list_frame.pack(fill="both", expand=True)

        # Rechte Spalte: Editor
        right = ctk.CTkFrame(body, fg_color=C["surface"], corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew")

        eh = ctk.CTkFrame(right, fg_color=C["surface"])
        eh.pack(fill="x", padx=12, pady=(10, 6))
        self._editor_title = ctk.CTkLabel(
            eh, text="Kein Profil ausgewaehlt",
            font=("Segoe UI", 14, "bold"), text_color=C["text"],
        )
        self._editor_title.pack(side="left")

        # Editor Buttons
        eb = ctk.CTkFrame(right, fg_color=C["surface"])
        eb.pack(fill="x", padx=12, pady=(0, 8))

        for text, color, hover, cmd in [
            ("Speichern", C["blue"], C["sky"], self._save_profile),
            ("Anwenden", C["mauve"], C["lavender"], self._apply_current_profile),
            ("Klonen", C["teal"], C["green"], self._clone_profile),
        ]:
            ctk.CTkButton(
                eb, text=text, fg_color=color, text_color=C["bg"],
                hover_color=hover, font=("Segoe UI", 11, "bold"),
                height=32, corner_radius=8, width=90, command=cmd,
            ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            eb, text="Loeschen", fg_color=C["card"], text_color=C["red"],
            hover_color=C["surface"], font=("Segoe UI", 11),
            height=32, corner_radius=8, width=80, command=self._delete_profile,
        ).pack(side="right")

        # Tabs: Visuell / JSON
        self._editor_tabs = ctk.CTkTabview(
            right, fg_color=C["surface"], corner_radius=8,
            segmented_button_fg_color=C["card"],
            segmented_button_selected_color=C["mauve"],
            segmented_button_unselected_color=C["surface"],
        )
        self._editor_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._editor_tabs.add("Visuell")
        self._editor_tabs.add("JSON")

        # Visueller Editor
        vis_tab = self._editor_tabs.tab("Visuell")
        self._visual_editor_frame = ctk.CTkScrollableFrame(
            vis_tab, fg_color=C["surface"], corner_radius=0)
        self._visual_editor_frame.pack(fill="both", expand=True)

        # JSON Editor
        json_tab = self._editor_tabs.tab("JSON")
        self._editor_text = ctk.CTkTextbox(
            json_tab, font=("Cascadia Code", 11),
            fg_color=C["card"], text_color=C["text"], corner_radius=8,
        )
        self._editor_text.pack(fill="both", expand=True)

        # Regelvorschau
        section_label(right, "REGELN (live)").pack(anchor="w", padx=12, pady=(0, 4))
        self._rules_frame = ctk.CTkScrollableFrame(
            right, fg_color=C["surface"], corner_radius=0, height=100)
        self._rules_frame.pack(fill="x", padx=12, pady=(0, 12))

        self._editor_text.bind("<KeyRelease>", lambda _: self._update_rules_preview())
        self._current_profile_key: str | None = None
        return f

    def _refresh_profiles(self):
        for w in self._profile_list_frame.winfo_children():
            w.destroy()

        for key, prof in sorted(profiles.items()):
            pkg_dir = Path(packages_root) / prof["package_folder"]
            found = pkg_dir.exists()
            enabled = prof.get("enabled", True)

            card = ctk.CTkFrame(
                self._profile_list_frame,
                fg_color=C["card"] if enabled else C["surface"],
                corner_radius=10,
            )
            card.pack(fill="x", padx=6, pady=3)

            # Toggle Switch
            def make_toggle(k=key, e=enabled):
                def toggle():
                    profiles[k]["enabled"] = not profiles[k].get("enabled", True)
                    fp = PROFILES_DIR / f"{k}.json"
                    fp.write_text(json.dumps(profiles[k], indent=2,
                                            ensure_ascii=False), "utf-8")
                    self._refresh_profiles()
                return toggle

            sw = ctk.CTkSwitch(
                card, text="", width=36, height=18,
                button_color=C["green"] if enabled else C["subtext"],
                progress_color=C["surface"],
                command=make_toggle(),
            )
            if enabled:
                sw.select()
            sw.pack(side="left", padx=(10, 4), pady=8)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, pady=6)

            name_color = C["text"] if enabled else C["subtext"]
            ctk.CTkLabel(info, text=prof.get("display_name", key),
                         font=("Segoe UI", 12, "bold"),
                         text_color=name_color, anchor="w").pack(anchor="w")

            sub_parts = [prof.get("package_folder", "")]
            if found:
                sub_parts.append("\u2713 gefunden")
            else:
                sub_parts.append("\u2717 nicht gefunden")
            ctk.CTkLabel(info, text=" \u2022 ".join(sub_parts),
                         font=("Segoe UI", 10),
                         text_color=C["green"] if found else C["yellow"],
                         anchor="w").pack(anchor="w")

            rule_count = len(prof.get("rules", []))
            badge(card, f"{rule_count}R", C["blue"]).pack(
                side="right", padx=4, pady=8)

            ctk.CTkButton(
                card, text="Bearbeiten", width=80,
                fg_color=C["border"], text_color=C["text"],
                hover_color=C["surface"], font=("Segoe UI", 10),
                height=28, corner_radius=6,
                command=lambda k=key: self._load_profile_to_editor(k),
            ).pack(side="right", padx=4, pady=8)

    def _load_profile_to_editor(self, key: str):
        self._current_profile_key = key
        f = PROFILES_DIR / f"{key}.json"
        if f.exists():
            text = f.read_text("utf-8")
            self._editor_text.delete("0.0", "end")
            self._editor_text.insert("0.0", text)
            prof = profiles.get(key, {})
            self._editor_title.configure(text=prof.get("display_name", key))
            self._update_rules_preview()
            self._update_visual_editor(prof)

    def _update_visual_editor(self, prof: dict):
        """Baut den visuellen Editor fuer ein Profil."""
        for w in self._visual_editor_frame.winfo_children():
            w.destroy()

        # Header-Infos
        info_card = ctk.CTkFrame(self._visual_editor_frame,
                                  fg_color=C["card"], corner_radius=10)
        info_card.pack(fill="x", padx=4, pady=(4, 8))

        for label, val in [
            ("Name:", prof.get("display_name", "")),
            ("Paket:", prof.get("package_folder", "")),
            ("Beschreibung:", prof.get("description", "")),
        ]:
            row = ctk.CTkFrame(info_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 11, "bold"),
                         text_color=C["subtext"], width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, font=("Segoe UI", 11),
                         text_color=C["text"], anchor="w").pack(side="left")

        # Regeln
        section_label(self._visual_editor_frame, "REGELN").pack(
            anchor="w", padx=4, pady=(8, 4))

        for i, rule in enumerate(prof.get("rules", [])):
            rule_card = ctk.CTkFrame(self._visual_editor_frame,
                                      fg_color=C["card"], corner_radius=8)
            rule_card.pack(fill="x", padx=4, pady=2)

            types_str = " + ".join(rule.get("source_types", []))
            target = rule.get("target", "")

            left = ctk.CTkFrame(rule_card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=6)

            ctk.CTkLabel(left, text=types_str, font=("Cascadia Code", 10),
                         text_color=C["teal"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(left, text=f"\u2192 {target}",
                         font=("Cascadia Code", 10),
                         text_color=C["peach"], anchor="w").pack(anchor="w")

            # Status-Check
            if self._current_profile_key:
                pkg_dir = Path(packages_root) / prof.get("package_folder", "")
                dest = pkg_dir / target
                if dest.exists() and is_link(dest):
                    badge(rule_card, "\u2713 Link", C["green"]).pack(
                        side="right", padx=8, pady=6)
                elif dest.exists():
                    badge(rule_card, "Ordner", C["yellow"]).pack(
                        side="right", padx=8, pady=6)
                else:
                    badge(rule_card, "Fehlt", C["red"]).pack(
                        side="right", padx=8, pady=6)

    def _update_rules_preview(self):
        for w in self._rules_frame.winfo_children():
            w.destroy()
        try:
            data = json.loads(self._editor_text.get("0.0", "end"))
            for rule in data.get("rules", []):
                row = ctk.CTkFrame(self._rules_frame, fg_color=C["card"],
                                   corner_radius=6)
                row.pack(fill="x", padx=4, pady=2)
                types_str = " + ".join(rule.get("source_types", []))
                ctk.CTkLabel(row, text=types_str, font=("Cascadia Code", 10),
                             text_color=C["teal"], anchor="w",
                             width=280).pack(side="left", padx=8, pady=4)
                ctk.CTkLabel(row, text="\u2192", font=("Segoe UI", 12),
                             text_color=C["subtext"]).pack(side="left")
                ctk.CTkLabel(row, text=rule.get("target", ""),
                             font=("Cascadia Code", 10),
                             text_color=C["peach"], anchor="w").pack(
                    side="left", padx=8, pady=4)
        except Exception:
            pass

    def _save_profile(self):
        if not self._current_profile_key:
            return
        text = self._editor_text.get("0.0", "end").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON-Fehler", str(e))
            return
        # Validierung
        warnings = []
        for rule in data.get("rules", []):
            for st in rule.get("source_types", []):
                if st not in master_types:
                    warnings.append(f"Unbekannter Typ: {st}")
        if warnings:
            if not messagebox.askyesno("Warnung",
                "Validierung:\n" + "\n".join(warnings) + "\n\nTrotzdem speichern?"):
                return

        fp = PROFILES_DIR / f"{self._current_profile_key}.json"
        fp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        reload_all()
        self._refresh_profiles()
        self._update_visual_editor(data)
        self._show_toast(f"Profil '{self._current_profile_key}' gespeichert")
        self._log(f"[Gespeichert] {self._current_profile_key}.json\n", C["green"])

    def _apply_current_profile(self):
        if not self._current_profile_key:
            return
        text = self._editor_text.get("0.0", "end").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON-Fehler", str(e))
            return
        self._run_apply([data], self._dry_var.get())

    def _clone_profile(self):
        if not self._current_profile_key:
            return
        text = self._editor_text.get("0.0", "end").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return
        new_key = f"{self._current_profile_key}_copy"
        i = 1
        while (PROFILES_DIR / f"{new_key}.json").exists():
            new_key = f"{self._current_profile_key}_copy{i}"
            i += 1
        data["name"] = data.get("name", "") + " (Kopie)"
        data["display_name"] = data.get("display_name", "") + " (Kopie)"
        fp = PROFILES_DIR / f"{new_key}.json"
        fp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        reload_all()
        self._refresh_profiles()
        self._load_profile_to_editor(new_key)
        self._show_toast(f"Profil geklont: {new_key}")

    def _delete_profile(self):
        if not self._current_profile_key:
            return
        if not messagebox.askyesno(
            "Profil loeschen",
            f"Profil '{self._current_profile_key}' wirklich loeschen?"
        ):
            return
        fp = PROFILES_DIR / f"{self._current_profile_key}.json"
        fp.unlink(missing_ok=True)
        self._current_profile_key = None
        self._editor_title.configure(text="Kein Profil ausgewaehlt")
        self._editor_text.delete("0.0", "end")
        for w in self._rules_frame.winfo_children():
            w.destroy()
        reload_all()
        self._refresh_profiles()

    def _new_profile(self):
        dialog = NewProfileDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            key = dialog.result["key"]
            data = dialog.result["data"]
            fp = PROFILES_DIR / f"{key}.json"
            if fp.exists():
                messagebox.showerror("Fehler", f"Profil '{key}' existiert bereits.")
                return
            fp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
            reload_all()
            self._refresh_profiles()
            self._load_profile_to_editor(key)

    # ── Downloader ─────────────────────────────────────────────

    def _build_downloader(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        ctk.CTkLabel(f, text="Model Downloader",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Modelle von CivitAI oder HuggingFace herunterladen",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            anchor="w", pady=(0, 12))

        if not HAS_DOWNLOADER:
            ctk.CTkLabel(f, text="Downloader-Modul nicht geladen (downloader.py fehlt)",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(
                anchor="w", pady=20)
            return f

        # URL-Eingabe
        url_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        url_card.pack(fill="x", pady=(0, 12))

        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(url_row, text="URL:", font=("Segoe UI", 12, "bold"),
                     text_color=C["text"], width=40).pack(side="left")

        self._dl_url_var = ctk.StringVar()
        self._dl_url_entry = ctk.CTkEntry(
            url_row, textvariable=self._dl_url_var,
            font=("Cascadia Code", 12), fg_color=C["surface"],
            border_color=C["border"], text_color=C["text"],
            placeholder_text="https://civitai.com/models/12345 oder HuggingFace URL...",
        )
        self._dl_url_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        ctk.CTkButton(
            url_row, text="Abrufen", width=90,
            fg_color=C["blue"], text_color=C["bg"],
            hover_color=C["sky"], font=("Segoe UI", 12, "bold"),
            height=34, corner_radius=8,
            command=self._fetch_model_info,
        ).pack(side="right")

        # Modell-Info Panel
        self._dl_info_frame = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        self._dl_info_frame.pack(fill="x", pady=(0, 12))
        self._dl_info_label = ctk.CTkLabel(
            self._dl_info_frame, text="Gib eine CivitAI oder HuggingFace URL ein...",
            font=("Segoe UI", 12), text_color=C["subtext"])
        self._dl_info_label.pack(padx=16, pady=16)

        # Datei-Auswahl (versteckt bis Modell geladen)
        self._dl_files_frame = ctk.CTkScrollableFrame(
            f, fg_color=C["surface"], corner_radius=12, height=120)
        self._dl_files_frame.pack(fill="x", pady=(0, 12))
        self._dl_files_frame.pack_forget()

        # Download-Typ Auswahl
        self._dl_type_var = ctk.StringVar(value="StableDiffusion")

        # Download Queue
        section_label(f, "DOWNLOAD-WARTESCHLANGE").pack(anchor="w", pady=(4, 6))
        self._dl_queue_frame = ctk.CTkScrollableFrame(
            f, fg_color=C["surface"], corner_radius=12)
        self._dl_queue_frame.pack(fill="both", expand=True)

        self._current_model_info: ModelInfo | None = None
        self._dl_update_timer()
        return f

    def _fetch_model_info(self):
        url = self._dl_url_var.get().strip()
        if not url:
            return

        self._dl_info_label.configure(text="Lade Modell-Informationen...",
                                       text_color=C["yellow"])

        def worker():
            try:
                source = detect_source(url)
                if source == "civitai":
                    client = CivitAIClient(api_key=civitai_api_key)
                    model_id = client.parse_url(url)
                    if not model_id:
                        raise ValueError("Ungueltige CivitAI URL")
                    info = client.fetch_model(model_id)
                elif source == "huggingface":
                    client = HuggingFaceClient()
                    repo_id = client.parse_url(url)
                    if not repo_id:
                        raise ValueError("Ungueltige HuggingFace URL")
                    info = client.fetch_model(repo_id)
                else:
                    raise ValueError("URL nicht erkannt (CivitAI/HuggingFace)")

                self.after(0, lambda: self._show_model_info(info))
            except Exception as e:
                self.after(0, lambda: self._dl_info_label.configure(
                    text=f"Fehler: {e}", text_color=C["red"]))

        threading.Thread(target=worker, daemon=True).start()

    def _show_model_info(self, info: ModelInfo):
        self._current_model_info = info

        # Info-Panel aktualisieren
        for w in self._dl_info_frame.winfo_children():
            w.destroy()

        grid = ctk.CTkFrame(self._dl_info_frame, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=12)

        # Modellname + Typ
        ctk.CTkLabel(grid, text=info.name, font=("Segoe UI", 16, "bold"),
                     text_color=C["text"]).pack(anchor="w")

        meta_row = ctk.CTkFrame(grid, fg_color="transparent")
        meta_row.pack(fill="x", pady=(4, 8))

        badge(meta_row, info.source.upper(), C["blue"]).pack(side="left", padx=(0, 6))
        badge(meta_row, info.model_type, C["peach"]).pack(side="left", padx=(0, 6))
        if info.base_model:
            badge(meta_row, info.base_model, C["teal"]).pack(side="left", padx=(0, 6))
        badge(meta_row, f"\u2192 {info.master_type}", C["mauve"]).pack(side="left")

        # Typ-Override
        type_row = ctk.CTkFrame(grid, fg_color="transparent")
        type_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(type_row, text="Ziel-Typ:", font=("Segoe UI", 11),
                     text_color=C["subtext"]).pack(side="left")
        self._dl_type_var.set(info.master_type)
        type_combo = ctk.CTkComboBox(
            type_row, variable=self._dl_type_var,
            values=sorted(master_types.keys()),
            font=("Segoe UI", 11), width=200,
            fg_color=C["surface"], border_color=C["border"],
        )
        type_combo.pack(side="left", padx=8)

        # Dateien anzeigen
        self._dl_files_frame.pack(fill="x", pady=(0, 12))
        for w in self._dl_files_frame.winfo_children():
            w.destroy()

        if info.versions:
            for v in info.versions[:5]:
                v_label = ctk.CTkLabel(
                    self._dl_files_frame,
                    text=f"Version: {v['name']} ({v.get('base_model', '')})",
                    font=("Segoe UI", 11, "bold"), text_color=C["lavender"],
                )
                v_label.pack(anchor="w", padx=8, pady=(6, 2))

                for fi in v.get("files", []):
                    file_row = ctk.CTkFrame(self._dl_files_frame,
                                            fg_color=C["card"], corner_radius=8)
                    file_row.pack(fill="x", padx=8, pady=2)

                    fname = fi.get("name", "?")
                    fsize = fi.get("size", 0)
                    furl = fi.get("url", "")

                    ctk.CTkLabel(file_row, text=fname,
                                 font=("Cascadia Code", 10),
                                 text_color=C["text"], anchor="w").pack(
                        side="left", padx=8, pady=6)

                    if fsize > 0:
                        ctk.CTkLabel(file_row, text=fmt_size(fsize),
                                     font=("Segoe UI", 10),
                                     text_color=C["subtext"]).pack(
                            side="left", padx=4)

                    if furl:
                        ctk.CTkButton(
                            file_row, text="\u2B07 Download", width=90,
                            fg_color=C["green"], text_color=C["bg"],
                            hover_color=C["teal"], font=("Segoe UI", 10, "bold"),
                            height=26, corner_radius=6,
                            command=lambda u=furl, n=fname, s=fsize:
                                self._start_download(u, n, info.name, s),
                        ).pack(side="right", padx=8, pady=4)

    def _start_download(self, url: str, filename: str, model_name: str,
                        file_size: int = 0):
        target_type = self._dl_type_var.get()
        dest_dir = master_folder(target_type)

        self._download_mgr.add_download(
            url=url,
            dest_dir=dest_dir,
            filename=filename,
            model_name=model_name,
            file_size=file_size,
        )
        self._show_toast(f"Download gestartet: {filename}")
        self._log(f"[Download] {filename} -> {dest_dir}\n", C["blue"])
        self._refresh_download_queue()

    def _on_download_progress(self, task: DownloadTask):
        pass  # Wird via Timer aktualisiert

    def _on_download_complete(self, task: DownloadTask):
        if task.status == "complete":
            self.after(0, lambda: self._show_toast(
                f"Download fertig: {task.filename}", C["green"]))
            self.after(0, lambda: self._log(
                f"[\u2713] Download fertig: {task.filename} "
                f"({fmt_size(task.file_size)})\n", C["green"]))
        elif task.status == "error":
            self.after(0, lambda: self._show_toast(
                f"Download fehlgeschlagen: {task.filename}", C["red"]))
            self.after(0, lambda: self._log(
                f"[\u2717] Download Fehler: {task.filename}: "
                f"{task.error_msg}\n", C["red"]))

    def _dl_update_timer(self):
        """Timer fuer Download-Queue Aktualisierung."""
        if self._active_idx == 2 and self._download_mgr:
            self._refresh_download_queue()
        self.after(1000, self._dl_update_timer)

    def _refresh_download_queue(self):
        if not self._download_mgr:
            return
        for w in self._dl_queue_frame.winfo_children():
            w.destroy()

        tasks = list(self._download_mgr.tasks)
        if not tasks:
            ctk.CTkLabel(self._dl_queue_frame,
                         text="Keine Downloads in der Warteschlange",
                         font=("Segoe UI", 12), text_color=C["subtext"]).pack(
                padx=16, pady=16)
            return

        for task in reversed(tasks):  # Neueste oben
            card = ctk.CTkFrame(self._dl_queue_frame,
                                fg_color=C["card"], corner_radius=10)
            card.pack(fill="x", padx=6, pady=3)

            # Status-Icon
            status_cfg = {
                "queued":      ("\u23F3", C["subtext"]),
                "downloading": ("\u2B07", C["blue"]),
                "complete":    ("\u2713", C["green"]),
                "error":       ("\u2717", C["red"]),
                "cancelled":   ("\u2716", C["yellow"]),
            }
            icon, color = status_cfg.get(task.status, ("?", C["text"]))
            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 16),
                         text_color=color, width=30).pack(
                side="left", padx=(10, 4))

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, pady=6)

            ctk.CTkLabel(info_frame, text=task.filename,
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")

            if task.status == "downloading":
                # Progress bar
                prog = ctk.CTkProgressBar(info_frame, height=6,
                                          fg_color=C["surface"],
                                          progress_color=C["blue"])
                prog.pack(fill="x", pady=(2, 0))
                prog.set(task.progress)

                speed_text = f"{fmt_size(task.downloaded)}"
                if task.file_size > 0:
                    speed_text += f" / {fmt_size(task.file_size)}"
                speed_text += f"  |  {fmt_speed(task.speed)}"
                speed_text += f"  |  {task.progress*100:.0f}%"
                ctk.CTkLabel(info_frame, text=speed_text,
                             font=("Segoe UI", 9),
                             text_color=C["subtext"]).pack(anchor="w")
            elif task.status == "complete":
                ctk.CTkLabel(info_frame,
                             text=f"Fertig: {fmt_size(task.file_size)}",
                             font=("Segoe UI", 10),
                             text_color=C["green"]).pack(anchor="w")
            elif task.status == "error":
                ctk.CTkLabel(info_frame, text=task.error_msg[:80],
                             font=("Segoe UI", 10),
                             text_color=C["red"]).pack(anchor="w")

            # Cancel Button
            if task.status in ("queued", "downloading"):
                ctk.CTkButton(
                    card, text="\u2716", width=30, height=28,
                    fg_color=C["surface"], text_color=C["red"],
                    hover_color=C["card"], font=("Segoe UI", 12),
                    corner_radius=6, command=task.cancel,
                ).pack(side="right", padx=8, pady=6)

    # ── Scanner ────────────────────────────────────────────────

    def _build_scanner(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])

        ctk.CTkLabel(f, text="Model Scanner",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Disk-Analyse, Duplikate und Waisen finden",
                     font=("Segoe UI", 12), text_color=C["subtext"]).pack(
            anchor="w", pady=(0, 12))

        if not HAS_SCANNER:
            ctk.CTkLabel(f, text="Scanner-Modul nicht geladen (scanner.py fehlt)",
                         font=("Segoe UI", 14), text_color=C["red"]).pack(
                anchor="w", pady=20)
            return f

        # Scan-Buttons
        btn_row = ctk.CTkFrame(f, fg_color=C["bg"])
        btn_row.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            btn_row, text="\u25C6  Ordnergroessen scannen",
            fg_color=C["teal"], text_color=C["bg"],
            hover_color=C["green"], font=("Segoe UI", 12, "bold"),
            height=38, corner_radius=8,
            command=self._scan_sizes,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="\u25C6  Duplikate finden",
            fg_color=C["peach"], text_color=C["bg"],
            hover_color=C["yellow"], font=("Segoe UI", 12, "bold"),
            height=38, corner_radius=8,
            command=self._scan_duplicates,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="\u25C6  Waisen finden",
            fg_color=C["blue"], text_color=C["bg"],
            hover_color=C["sky"], font=("Segoe UI", 12, "bold"),
            height=38, corner_radius=8,
            command=self._scan_orphans,
        ).pack(side="left")

        # Progress
        self._scan_progress = ctk.CTkProgressBar(
            f, height=6, fg_color=C["surface"],
            progress_color=C["teal"])
        self._scan_progress.pack(fill="x", pady=(0, 4))
        self._scan_progress.set(0)
        self._scan_status = ctk.CTkLabel(
            f, text="Bereit zum Scannen",
            font=("Segoe UI", 10), text_color=C["subtext"])
        self._scan_status.pack(anchor="w", pady=(0, 8))

        # Ergebnis-Tabs
        self._scan_tabs = ctk.CTkTabview(
            f, fg_color=C["bg"], corner_radius=10,
            segmented_button_fg_color=C["card"],
            segmented_button_selected_color=C["mauve"],
            segmented_button_unselected_color=C["surface"],
        )
        self._scan_tabs.pack(fill="both", expand=True)
        self._scan_tabs.add("Ordnergroessen")
        self._scan_tabs.add("Duplikate")
        self._scan_tabs.add("Waisen")

        # Ergebnis-Frames
        self._scan_sizes_frame = ctk.CTkScrollableFrame(
            self._scan_tabs.tab("Ordnergroessen"),
            fg_color=C["bg"], corner_radius=0)
        self._scan_sizes_frame.pack(fill="both", expand=True)

        self._scan_dupes_frame = ctk.CTkScrollableFrame(
            self._scan_tabs.tab("Duplikate"),
            fg_color=C["bg"], corner_radius=0)
        self._scan_dupes_frame.pack(fill="both", expand=True)

        self._scan_orphans_frame = ctk.CTkScrollableFrame(
            self._scan_tabs.tab("Waisen"),
            fg_color=C["bg"], corner_radius=0)
        self._scan_orphans_frame.pack(fill="both", expand=True)

        return f

    def _scan_sizes(self):
        self._scan_status.configure(text="Scanne Ordnergroessen...",
                                     text_color=C["teal"])
        self._scan_progress.set(0)

        def progress_cb(done, total, name):
            self.after(0, lambda: self._scan_progress.set(done / max(total, 1)))
            self.after(0, lambda: self._scan_status.configure(
                text=f"Scanne: {name} ({done}/{total})"))

        def worker():
            results = scan_folder_sizes(master_root, master_types, progress_cb)
            self.after(0, lambda: self._show_scan_sizes(results))

        threading.Thread(target=worker, daemon=True).start()

    def _show_scan_sizes(self, results: list):
        for w in self._scan_sizes_frame.winfo_children():
            w.destroy()

        total_bytes = sum(r.total_bytes for r in results)
        total_files = sum(r.file_count for r in results)
        total_models = sum(r.model_count for r in results)

        # Zusammenfassung
        summary = ctk.CTkFrame(self._scan_sizes_frame,
                                fg_color=C["card"], corner_radius=10)
        summary.pack(fill="x", padx=4, pady=(4, 12))
        ctk.CTkLabel(summary,
                     text=f"Gesamt: {scan_fmt_size(total_bytes)}  |  "
                          f"{total_files} Dateien  |  {total_models} Modelle",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C["text"]).pack(padx=16, pady=10)

        # Header
        hdr = ctk.CTkFrame(self._scan_sizes_frame, fg_color=C["surface"],
                            corner_radius=6)
        hdr.pack(fill="x", padx=4, pady=(0, 4))
        for text, w in [("Typ", 140), ("Ordner", 130), ("Dateien", 60),
                        ("Modelle", 60), ("Groesse", 80), ("Groesste", 160)]:
            ctk.CTkLabel(hdr, text=text, font=("Segoe UI", 10, "bold"),
                         text_color=C["subtext"], width=w, anchor="w").pack(
                side="left", padx=4, pady=4)

        # Zeilen
        for r in sorted(results, key=lambda x: -x.total_bytes):
            row = ctk.CTkFrame(self._scan_sizes_frame,
                                fg_color=C["card"], corner_radius=6)
            row.pack(fill="x", padx=4, pady=1)

            name_color = C["text"] if r.exists else C["subtext"]
            size_color = C["green"] if r.total_bytes > 0 else C["subtext"]

            for text, w, color in [
                (r.key, 140, C["lavender"]),
                (r.label, 130, name_color),
                (str(r.file_count), 60, C["text"]),
                (str(r.model_count), 60, C["blue"]),
                (scan_fmt_size(r.total_bytes), 80, size_color),
                (r.largest_file[:25] if r.largest_file else "-", 160, C["subtext"]),
            ]:
                ctk.CTkLabel(row, text=text, font=("Segoe UI", 10),
                             text_color=color, width=w, anchor="w").pack(
                    side="left", padx=4, pady=4)

            if r.is_symlink:
                badge(row, "Link", C["teal"]).pack(side="right", padx=4)
            elif not r.exists:
                badge(row, "Fehlt", C["yellow"]).pack(side="right", padx=4)

        self._scan_status.configure(text=f"Scan fertig: {scan_fmt_size(total_bytes)} gesamt",
                                     text_color=C["green"])
        self._scan_progress.set(1.0)
        self._scan_tabs.set("Ordnergroessen")

    def _scan_duplicates(self):
        self._scan_status.configure(text="Suche Duplikate...",
                                     text_color=C["peach"])
        self._scan_progress.set(0)

        def progress_cb(done, total, name):
            self.after(0, lambda: self._scan_progress.set(done / max(total, 1)))

        def worker():
            dupes = find_duplicates(master_root, progress_cb)
            self.after(0, lambda: self._show_scan_dupes(dupes))

        threading.Thread(target=worker, daemon=True).start()

    def _show_scan_dupes(self, dupes: list):
        for w in self._scan_dupes_frame.winfo_children():
            w.destroy()

        if not dupes:
            ctk.CTkLabel(self._scan_dupes_frame,
                         text="Keine Duplikate gefunden!",
                         font=("Segoe UI", 14, "bold"),
                         text_color=C["green"]).pack(padx=16, pady=20)
            self._scan_status.configure(text="Keine Duplikate gefunden",
                                         text_color=C["green"])
            self._scan_progress.set(1.0)
            self._scan_tabs.set("Duplikate")
            return

        wasted = sum(g.size * (len(g.files) - 1) for g in dupes)
        ctk.CTkLabel(self._scan_dupes_frame,
                     text=f"{len(dupes)} Duplikat-Gruppen  |  "
                          f"Verschwendet: {scan_fmt_size(wasted)}",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C["yellow"]).pack(padx=8, pady=(8, 12))

        for g in dupes:
            card = ctk.CTkFrame(self._scan_dupes_frame,
                                fg_color=C["card"], corner_radius=10)
            card.pack(fill="x", padx=4, pady=4)

            ctk.CTkLabel(card,
                         text=f"Groesse: {scan_fmt_size(g.size)}  |  "
                              f"{len(g.files)} Dateien  |  Hash: {g.hash_val}",
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["peach"]).pack(anchor="w", padx=12, pady=(8, 4))

            for fp in g.files:
                file_row = ctk.CTkFrame(card, fg_color=C["surface"],
                                         corner_radius=6)
                file_row.pack(fill="x", padx=12, pady=1)
                ctk.CTkLabel(file_row, text=str(fp),
                             font=("Cascadia Code", 9),
                             text_color=C["text"], anchor="w").pack(
                    side="left", padx=8, pady=4, fill="x", expand=True)

                if sys.platform == "win32":
                    ctk.CTkButton(
                        file_row, text="\u2630", width=28, height=24,
                        fg_color=C["card"], text_color=C["subtext"],
                        hover_color=C["border"], font=("Segoe UI", 10),
                        corner_radius=4,
                        command=lambda p=fp: subprocess.Popen(
                            ["explorer", "/select,", str(p)]),
                    ).pack(side="right", padx=4, pady=2)

        self._scan_status.configure(
            text=f"{len(dupes)} Duplikat-Gruppen, {scan_fmt_size(wasted)} verschwendet",
            text_color=C["peach"])
        self._scan_progress.set(1.0)
        self._scan_tabs.set("Duplikate")

    def _scan_orphans(self):
        self._scan_status.configure(text="Suche verwaiste Modelldateien...",
                                     text_color=C["blue"])
        self._scan_progress.set(0)

        def progress_cb(done, total, name):
            self.after(0, lambda: self._scan_progress.set(done / max(total, 1)))

        def worker():
            orphans = find_orphans(packages_root, profiles, progress_cb)
            self.after(0, lambda: self._show_scan_orphans(orphans))

        threading.Thread(target=worker, daemon=True).start()

    def _show_scan_orphans(self, orphans: list):
        for w in self._scan_orphans_frame.winfo_children():
            w.destroy()

        if not orphans:
            ctk.CTkLabel(self._scan_orphans_frame,
                         text="Keine verwaisten Dateien gefunden!",
                         font=("Segoe UI", 14, "bold"),
                         text_color=C["green"]).pack(padx=16, pady=20)
            self._scan_status.configure(text="Keine Waisen gefunden",
                                         text_color=C["green"])
            self._scan_progress.set(1.0)
            self._scan_tabs.set("Waisen")
            return

        total_size = sum(o.size for o in orphans)
        ctk.CTkLabel(self._scan_orphans_frame,
                     text=f"{len(orphans)} verwaiste Dateien  |  "
                          f"Gesamt: {scan_fmt_size(total_size)}",
                     font=("Segoe UI", 13, "bold"),
                     text_color=C["blue"]).pack(padx=8, pady=(8, 12))

        ctk.CTkLabel(self._scan_orphans_frame,
                     text="Diese Dateien liegen direkt in WebUI-Ordnern statt im Master-Root.",
                     font=("Segoe UI", 11), text_color=C["subtext"]).pack(
            padx=8, pady=(0, 8))

        for o in orphans[:100]:  # Max 100 anzeigen
            card = ctk.CTkFrame(self._scan_orphans_frame,
                                fg_color=C["card"], corner_radius=8)
            card.pack(fill="x", padx=4, pady=2)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=10, pady=4)

            ctk.CTkLabel(info, text=o.path.name,
                         font=("Segoe UI", 11, "bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"{o.webui_name}  |  {scan_fmt_size(o.size)}  |  "
                              f"Typ: {o.suggested_type}",
                         font=("Segoe UI", 10),
                         text_color=C["subtext"], anchor="w").pack(anchor="w")

            badge(card, o.suggested_type, C["peach"]).pack(
                side="right", padx=8, pady=4)

        self._scan_status.configure(
            text=f"{len(orphans)} Waisen, {scan_fmt_size(total_size)} gesamt",
            text_color=C["blue"])
        self._scan_progress.set(1.0)
        self._scan_tabs.set("Waisen")

    # ── Master-Typen ──────────────────────────────────────────

    def _build_types(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])
        ctk.CTkLabel(f, text="Master-Typen",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))

        self._types_root_label = ctk.CTkLabel(
            f, text=f"Master-Root: {master_root}",
            font=("Cascadia Code", 11), text_color=C["blue"],
        )
        self._types_root_label.pack(anchor="w", pady=(0, 12))

        brow = ctk.CTkFrame(f, fg_color=C["bg"])
        brow.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            brow, text="Fehlende Ordner erstellen",
            fg_color=C["teal"], text_color=C["bg"],
            hover_color=C["green"], font=("Segoe UI", 12, "bold"),
            height=36, corner_radius=8,
            command=self._create_missing_folders,
        ).pack(side="left")

        # Grid
        grid = ctk.CTkScrollableFrame(f, fg_color=C["surface"], corner_radius=12)
        grid.pack(fill="both", expand=True)

        grid.columnconfigure(0, minsize=180, weight=0)
        grid.columnconfigure(1, minsize=160, weight=0)
        grid.columnconfigure(2, minsize=200, weight=1)
        grid.columnconfigure(3, minsize=80, weight=0)

        hdrs = ["Typ-Key", "Ordner", "Beschreibung", "Status"]
        for col, h in enumerate(hdrs):
            ctk.CTkLabel(grid, text=h, font=("Segoe UI", 10, "bold"),
                         text_color=C["subtext"]).grid(
                row=0, column=col, sticky="w", padx=8, pady=(8, 4))

        self._types_grid = grid
        return f

    def _refresh_types(self):
        for w in self._types_grid.winfo_children():
            info = w.grid_info()
            if info.get("row", 0) > 0:
                w.destroy()

        self._types_root_label.configure(text=f"Master-Root: {master_root}")

        for row, (key, mt) in enumerate(sorted(master_types.items()), start=1):
            path = master_folder(key)
            exists = path.exists()
            linked = is_link(path) if exists else False

            ctk.CTkLabel(self._types_grid, text=key,
                         font=("Cascadia Code", 10),
                         text_color=C["lavender"],
                         anchor="w").grid(row=row, column=0,
                                          sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self._types_grid, text=mt.get("folder", ""),
                         font=("Cascadia Code", 10),
                         text_color=C["peach"], anchor="w").grid(
                row=row, column=1, sticky="w", padx=8)
            ctk.CTkLabel(self._types_grid, text=mt.get("description", ""),
                         font=("Segoe UI", 10),
                         text_color=C["subtext"], anchor="w").grid(
                row=row, column=2, sticky="w", padx=8)

            status_text = "\u2713 Vorhanden" if exists else "\u2717 Fehlt"
            if linked:
                status_text = "\u2194 Link"
            ctk.CTkLabel(
                self._types_grid,
                text=status_text,
                font=("Segoe UI", 10, "bold"),
                text_color=C["green"] if exists else C["yellow"],
            ).grid(row=row, column=3, padx=8)

    def _create_missing_folders(self):
        created = 0
        for key in master_types:
            p = master_folder(key)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
                created += 1
                self._log(f"[Erstellt] {p}\n", C["teal"])
        self._refresh_types()
        self._show_toast(f"{created} Ordner erstellt")

    # ── Einstellungen ─────────────────────────────────────────

    def _build_settings(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])
        ctk.CTkLabel(f, text="Einstellungen",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 16))

        # Pfad-Einstellungen
        section_label(f, "PFADE").pack(anchor="w", pady=(0, 6))
        card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        card.pack(fill="x", pady=(0, 16))

        def path_row(parent, label: str, var: ctk.StringVar, browse_cb):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=8)
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 12),
                         text_color=C["text"], width=160, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, textvariable=var, font=("Cascadia Code", 11),
                                 fg_color=C["surface"], border_color=C["border"],
                                 text_color=C["text"], width=420)
            entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
            ctk.CTkButton(row, text="\u2630", width=38, height=32,
                          fg_color=C["surface"], hover_color=C["border"],
                          text_color=C["text"], font=("Segoe UI", 14),
                          command=browse_cb).pack(side="left")

        self._master_var = ctk.StringVar(value=master_root)
        self._pkg_var = ctk.StringVar(value=packages_root)

        path_row(card, "Master-Root:", self._master_var,
                 lambda: self._browse(self._master_var))
        path_row(card, "Packages-Root:", self._pkg_var,
                 lambda: self._browse(self._pkg_var))

        # API-Einstellungen
        section_label(f, "API KEYS").pack(anchor="w", pady=(0, 6))
        api_card = ctk.CTkFrame(f, fg_color=C["card"], corner_radius=12)
        api_card.pack(fill="x", pady=(0, 16))

        api_row = ctk.CTkFrame(api_card, fg_color="transparent")
        api_row.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(api_row, text="CivitAI API Key:", font=("Segoe UI", 12),
                     text_color=C["text"], width=160, anchor="w").pack(side="left")
        self._civitai_key_var = ctk.StringVar(value=civitai_api_key)
        ctk.CTkEntry(api_row, textvariable=self._civitai_key_var,
                     font=("Cascadia Code", 11), show="*",
                     fg_color=C["surface"], border_color=C["border"],
                     text_color=C["text"]).pack(
            side="left", padx=(0, 8), fill="x", expand=True)

        ctk.CTkLabel(api_card,
                     text="  Optional: Fuer schnellere Downloads und NSFW-Modelle",
                     font=("Segoe UI", 10), text_color=C["subtext"]).pack(
            anchor="w", padx=16, pady=(0, 8))

        # Speichern
        ctk.CTkButton(
            f, text="Einstellungen speichern",
            fg_color=C["blue"], text_color=C["bg"],
            hover_color=C["sky"], font=("Segoe UI", 13, "bold"),
            height=42, corner_radius=10,
            command=self._save_settings_ui,
        ).pack(anchor="w", pady=8)

        # Info
        info = ctk.CTkFrame(f, fg_color=C["surface"], corner_radius=12)
        info.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(info, text=(
            "  Master-Root:    Globale Modellbibliothek (SharedFolderType-Ordner).\n"
            "  Packages-Root:  StabilityMatrix Packages-Verzeichnis.\n\n"
            "  Die Anwendung erstellt Junction-Points (Windows) bzw. Symlinks.\n"
            "  CivitAI API Key: Erhaeltlich unter civitai.com/user/account"
        ), font=("Segoe UI", 11), text_color=C["subtext"],
                     justify="left", anchor="w").pack(padx=16, pady=12)
        return f

    def _browse(self, var: ctk.StringVar):
        d = filedialog.askdirectory(initialdir=var.get() or "/")
        if d:
            var.set(d)

    def _save_settings_ui(self):
        global master_root, packages_root, civitai_api_key
        master_root = self._master_var.get()
        packages_root = self._pkg_var.get()
        civitai_api_key = self._civitai_key_var.get()
        save_settings()
        reload_all()
        self._update_statusbar()
        self._show_toast("Einstellungen gespeichert")
        self._log(f"[Gespeichert] Master: {master_root}\n", C["green"])
        self._log(f"[Gespeichert] Packages: {packages_root}\n", C["green"])

    # ── Log ───────────────────────────────────────────────────

    def _build_log(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self.main, fg_color=C["bg"])
        hdr = ctk.CTkFrame(f, fg_color=C["bg"])
        hdr.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Ausfuehrungs-Log",
                     font=("Segoe UI", 24, "bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkButton(hdr, text="Leeren", width=80, height=32,
                      fg_color=C["card"], text_color=C["subtext"],
                      hover_color=C["surface"], font=("Segoe UI", 11),
                      corner_radius=8, command=self._log_clear).pack(side="right")

        self._log_box = ctk.CTkTextbox(
            f, font=("Cascadia Code", 11),
            fg_color=C["card"], text_color=C["text"],
            corner_radius=12, state="disabled",
        )
        self._log_box.pack(fill="both", expand=True)
        return f

    def _log(self, text: str, color: str = None):
        def _do():
            self._log_box.configure(state="normal")
            if color:
                tag = f"col_{color.replace('#', '')}"
                self._log_box.tag_config(tag, foreground=color)
                self._log_box.insert("end", text, tag)
            else:
                self._log_box.insert("end", text)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _do)

    def _log_clear(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("0.0", "end")
        self._log_box.configure(state="disabled")

    # ── Globales Refresh ──────────────────────────────────────

    def refresh_all(self):
        if self._active_idx == 0:
            self._refresh_dashboard()
        elif self._active_idx == 1:
            self._refresh_profiles()
        elif self._active_idx == 4:
            self._refresh_types()
        self._update_statusbar()


# ─────────────────────────── Dialoge ─────────────────────────

class NewProfileDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Neues Profil erstellen")
        self.geometry("520x480")
        self.configure(fg_color=C["bg"])
        self.grab_set()
        self.result = None
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Neues WebUI-Profil",
                     font=("Segoe UI", 18, "bold"),
                     text_color=C["text"]).pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Erstelle ein neues Profil fuer eine WebUI",
                     font=("Segoe UI", 11), text_color=C["subtext"]).pack(
            pady=(0, 12))

        form = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=12)
        form.pack(fill="x", padx=20, pady=10)

        fields = [
            ("Profil-Key:", "key", "MeinWebUI"),
            ("Anzeigename:", "display_name", "Mein WebUI"),
            ("Paketordner:", "package_folder", "mein-webui"),
            ("Beschreibung:", "description", ""),
        ]
        self._vars = {}
        for label, key, placeholder in fields:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 11),
                         text_color=C["subtext"], width=140, anchor="w").pack(side="left")
            v = ctk.StringVar(value=placeholder)
            ctk.CTkEntry(row, textvariable=v, font=("Segoe UI", 11),
                         fg_color=C["surface"], border_color=C["border"],
                         text_color=C["text"]).pack(side="left", fill="x", expand=True)
            self._vars[key] = v

        self._enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(form, text="Aktiviert",
                      variable=self._enabled_var,
                      text_color=C["text"]).pack(anchor="w", padx=12, pady=8)

        # Template-Auswahl
        section_label(form, "VORLAGE").pack(anchor="w", padx=12, pady=(8, 4))
        self._template_var = ctk.StringVar(value="Standard SD1.5/XL")
        ctk.CTkComboBox(
            form, variable=self._template_var,
            values=["Standard SD1.5/XL", "ComfyUI-Stil", "Minimal",
                    "Flux-optimiert", "Training (Kohya)"],
            font=("Segoe UI", 11), fg_color=C["surface"],
            border_color=C["border"],
        ).pack(anchor="w", padx=12, pady=(0, 12))

        btns = ctk.CTkFrame(self, fg_color=C["bg"])
        btns.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(btns, text="Erstellen",
                      fg_color=C["blue"], text_color=C["bg"],
                      hover_color=C["sky"], font=("Segoe UI", 12, "bold"),
                      height=38, corner_radius=8,
                      command=self._submit).pack(side="left")
        ctk.CTkButton(btns, text="Abbrechen",
                      fg_color=C["card"], text_color=C["subtext"],
                      hover_color=C["surface"], font=("Segoe UI", 12),
                      height=38, corner_radius=8,
                      command=self.destroy).pack(side="right")

    def _submit(self):
        key = self._vars["key"].get().strip()
        if not key:
            messagebox.showerror("Fehler", "Key darf nicht leer sein.")
            return

        template = self._template_var.get()
        rules = self._get_template_rules(template)

        self.result = {
            "key": key,
            "data": {
                "name":           self._vars["display_name"].get(),
                "display_name":   self._vars["display_name"].get(),
                "package_folder": self._vars["package_folder"].get(),
                "enabled":        self._enabled_var.get(),
                "description":    self._vars["description"].get(),
                "rules":          rules,
            },
        }
        self.destroy()

    def _get_template_rules(self, template: str) -> list:
        templates = {
            "Standard SD1.5/XL": [
                {"source_types": ["StableDiffusion"], "target": "models/Stable-diffusion"},
                {"source_types": ["Lora", "LyCORIS"], "target": "models/Lora"},
                {"source_types": ["VAE"], "target": "models/VAE"},
                {"source_types": ["ControlNet"], "target": "models/ControlNet"},
                {"source_types": ["Embeddings"], "target": "embeddings"},
                {"source_types": ["ESRGAN", "RealESRGAN", "SwinIR"], "target": "models/ESRGAN"},
                {"source_types": ["Hypernetwork"], "target": "models/hypernetworks"},
            ],
            "ComfyUI-Stil": [
                {"source_types": ["StableDiffusion"], "target": "models/checkpoints"},
                {"source_types": ["Lora"], "target": "models/loras"},
                {"source_types": ["VAE"], "target": "models/vae"},
                {"source_types": ["ControlNet"], "target": "models/controlnet"},
                {"source_types": ["Embeddings"], "target": "models/embeddings"},
                {"source_types": ["ESRGAN", "RealESRGAN"], "target": "models/upscale_models"},
                {"source_types": ["ClipVision"], "target": "models/clip_vision"},
                {"source_types": ["TextEncoders"], "target": "models/text_encoders"},
                {"source_types": ["DiffusionModels"], "target": "models/diffusion_models"},
                {"source_types": ["IpAdapter"], "target": "models/ipadapter"},
                {"source_types": ["GLIGEN"], "target": "models/gligen"},
            ],
            "Minimal": [
                {"source_types": ["StableDiffusion"], "target": "models/checkpoints"},
                {"source_types": ["Lora"], "target": "models/loras"},
                {"source_types": ["VAE"], "target": "models/vae"},
            ],
            "Flux-optimiert": [
                {"source_types": ["StableDiffusion"], "target": "models/checkpoints"},
                {"source_types": ["Lora"], "target": "models/loras"},
                {"source_types": ["VAE"], "target": "models/vae"},
                {"source_types": ["TextEncoders"], "target": "models/text_encoders"},
                {"source_types": ["DiffusionModels"], "target": "models/diffusion_models"},
                {"source_types": ["ClipVision"], "target": "models/clip_vision"},
                {"source_types": ["ControlNet"], "target": "models/controlnet"},
            ],
            "Training (Kohya)": [
                {"source_types": ["StableDiffusion"], "target": "models"},
                {"source_types": ["Lora"], "target": "output"},
                {"source_types": ["VAE"], "target": "vae"},
            ],
        }
        return templates.get(template, templates["Standard SD1.5/XL"])


# ─────────────────────────── Start ───────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
