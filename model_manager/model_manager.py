"""
SD Model Manager
================
Liest Master-Typen und WebUI-Profile aus JSON,
erstellt oder aktualisiert Junction-Links (Windows) bzw. Symlinks (Linux/Mac).

Aufruf:
    python model_manager.py                    # GUI
    python model_manager.py --cli              # CLI
    python model_manager.py --cli --dry-run    # Vorschau
    python model_manager.py --cli --profile ComfyUI  # nur ein Profil
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────── Pfade ───────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
PROFILES_DIR = BASE_DIR / "profiles"
MASTER_TYPES_FILE = CONFIG_DIR / "master_types.json"

# ─────────────────────────── Datenmodelle ────────────────────

@dataclass
class MasterType:
    key: str
    folder: str
    label: str
    description: str

    @property
    def full_path(self) -> Path:
        return Path(master_root) / self.folder


@dataclass
class ProfileRule:
    source_types: list[str]
    target: str


@dataclass
class Profile:
    name: str
    display_name: str
    package_folder: str
    enabled: bool
    description: str
    rules: list[ProfileRule]
    inherits: Optional[str] = None
    filename: str = ""


# ─────────────────────────── Laden ───────────────────────────

master_root: str = ""
master_types: dict[str, MasterType] = {}
profiles: dict[str, Profile] = {}


def load_master_types() -> None:
    global master_root, master_types
    data = json.loads(MASTER_TYPES_FILE.read_text(encoding="utf-8"))
    master_root = data["master_root"]
    master_types = {
        key: MasterType(key=key, folder=v["folder"], label=v["label"], description=v["description"])
        for key, v in data["types"].items()
    }
    print(f"[OK] Master-Root: {master_root}")
    print(f"[OK] {len(master_types)} Typen geladen")


def load_profiles() -> None:
    global profiles
    profiles = {}
    for f in sorted(PROFILES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            rules = [
                ProfileRule(source_types=r["source_types"], target=r["target"])
                for r in data.get("rules", [])
            ]
            p = Profile(
                name=data["name"],
                display_name=data["display_name"],
                package_folder=data["package_folder"],
                enabled=data.get("enabled", True),
                description=data.get("description", ""),
                rules=rules,
                inherits=data.get("inherits"),
                filename=f.stem,
            )
            profiles[f.stem] = p
        except Exception as e:
            print(f"[WARN] Profil '{f.name}' konnte nicht geladen werden: {e}")
    print(f"[OK] {len(profiles)} Profile geladen")


def reload_all() -> None:
    load_master_types()
    load_profiles()


# ─────────────────────────── Symlink-Logik ───────────────────

def is_windows() -> bool:
    return sys.platform == "win32"


def is_junction_or_symlink(path: Path) -> bool:
    try:
        return path.is_symlink() or (is_windows() and path.stat().st_reparse_tag == 0xa0000003)
    except Exception:
        return path.is_symlink()


def create_link(source: Path, target: Path, dry_run: bool = False) -> tuple[str, str]:
    """
    Erstellt einen Junction/Symlink von target -> source.
    source = Master-Ordner (Ziel des Links)
    target = WebUI-Ordner (der Link selbst)

    Gibt (status, message) zurueck.
    status: "ok" | "skip" | "warn" | "error" | "dry"
    """
    # Sicherstellen dass source existiert
    if not dry_run:
        source.mkdir(parents=True, exist_ok=True)

    # Pruefen ob target bereits existiert
    if target.exists() or target.is_symlink():
        # Bereits ein Link?
        if is_junction_or_symlink(target):
            try:
                existing = Path(os.readlink(str(target)))
                if existing == source:
                    return "skip", f"Unveraendert: {target.name}"
            except Exception:
                pass
            if not dry_run:
                # Alten Link entfernen
                if is_windows():
                    subprocess.run(["cmd", "/c", "rmdir", str(target)], capture_output=True)
                else:
                    target.unlink()
        else:
            # Echter Ordner - Dateien verschieben
            files = list(target.rglob("*"))
            if files:
                if not dry_run:
                    for item in target.iterdir():
                        dest = source / item.name
                        if not dest.exists():
                            item.rename(dest)
                        else:
                            return "warn", f"Konflikt - Ordner existiert mit Dateien: {target}"
                if dry_run:
                    return "dry", f"[VORSCHAU] Dateien verschieben + Link: {target} -> {source}"

            if not dry_run:
                import shutil
                shutil.rmtree(str(target), ignore_errors=True)

    if dry_run:
        return "dry", f"[VORSCHAU] Link erstellen: {target} -> {source}"

    # Link erstellen
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if is_windows():
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                # Fallback: Symlink (erfordert Developer Mode oder Admin)
                os.symlink(str(source), str(target))
        else:
            os.symlink(str(source), str(target))
        return "ok", f"Link erstellt: {target.name} -> {source}"
    except Exception as e:
        return "error", f"Fehler bei {target}: {e}"


def apply_profile(
    profile: Profile,
    packages_root: Path,
    dry_run: bool = False,
    verbose: bool = True,
) -> list[tuple[str, str]]:
    """
    Wendet ein Profil an: erstellt alle Junction-Links fuer eine WebUI.
    Gibt Liste von (status, message) zurueck.
    """
    results = []
    package_dir = packages_root / profile.package_folder

    if not package_dir.exists() and not dry_run:
        results.append(("warn", f"Paket-Ordner nicht gefunden: {package_dir}"))
        return results

    for rule in profile.rules:
        # Ziel-Pfad innerhalb der WebUI
        target = package_dir / rule.target

        # Fuer jeden source_type einen Link erstellen
        # Normalfall: alle source_types -> ein target (kombiniert)
        # Sonderfall: mehrere source_types -> ein einzelner target-Ordner
        # Wir linken den ersten gueltigen source_type als Hauptquelle
        # und die restlichen werden per Sub-Symlink eingebunden

        if len(rule.source_types) == 1:
            # Einfacher Fall: ein Typ -> ein Ordner
            key = rule.source_types[0]
            if key not in master_types:
                results.append(("warn", f"Unbekannter Typ: {key}"))
                continue
            source = master_types[key].full_path
            status, msg = create_link(source, target, dry_run)
            results.append((status, f"[{profile.display_name}] {msg}"))
        else:
            # Mehrere Typen -> kombinierter Ordner
            # Wir erstellen den Ordner und linken jeden Typ als Unterordner
            # ODER (wie ComfyUI es macht): alles in einen gemeinsamen Ordner
            # Strategie: target = echter Ordner, jeder source_type = Sub-Junction
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)

            for key in rule.source_types:
                if key not in master_types:
                    results.append(("warn", f"Unbekannter Typ: {key}"))
                    continue
                mt = master_types[key]
                sub_target = target / mt.folder
                source = mt.full_path
                status, msg = create_link(source, sub_target, dry_run)
                results.append((status, f"[{profile.display_name}] {rule.target}/{mt.folder}: {status}"))

    return results


def get_packages_root() -> Path:
    """Ermittelt den Packages-Root aus dem Master-Root."""
    # Master ist z.B. D:\Programme\stability_matrix\models
    # Packages sind D:\Programme\stability_matrix\Packages
    master = Path(master_root)
    return master.parent / "Packages"


# ─────────────────────────── CLI ─────────────────────────────

def run_cli(args) -> None:
    reload_all()
    packages_root = get_packages_root()

    print(f"\n{'='*60}")
    print(f"  SD Model Manager - CLI")
    print(f"{'='*60}")
    print(f"  Master-Root:   {master_root}")
    print(f"  Packages-Root: {packages_root}")
    print(f"  Dry-Run:       {args.dry_run}")
    print(f"{'='*60}\n")

    # Profile filtern
    selected = {}
    if args.profile:
        for p in args.profile:
            if p in profiles:
                selected[p] = profiles[p]
            else:
                print(f"[WARN] Profil '{p}' nicht gefunden. Verfuegbare: {list(profiles.keys())}")
    else:
        selected = profiles

    if not selected:
        print("[ERROR] Keine Profile gefunden.")
        return

    total_ok = total_skip = total_warn = total_error = 0

    for key, profile in selected.items():
        if not profile.enabled and not args.all:
            print(f"[SKIP] {profile.display_name} (deaktiviert, nutze --all zum Erzwingen)")
            continue

        print(f"\n>> {profile.display_name} ({profile.package_folder})")
        print(f"   {profile.description}")

        results = apply_profile(
            profile, packages_root, dry_run=args.dry_run, verbose=args.verbose
        )

        for status, msg in results:
            symbol = {"ok": "✓", "skip": "─", "warn": "!", "error": "✗", "dry": "~"}.get(status, "?")
            print(f"   {symbol} {msg}")
            if status == "ok":     total_ok += 1
            elif status == "skip": total_skip += 1
            elif status == "warn": total_warn += 1
            elif status == "error":total_error += 1

    print(f"\n{'='*60}")
    print(f"  Ergebnis: {total_ok} erstellt | {total_skip} unveraendert | {total_warn} Warnungen | {total_error} Fehler")
    print(f"{'='*60}\n")


# ─────────────────────────── GUI ─────────────────────────────

def run_gui() -> None:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
    import threading

    reload_all()

    # ── Hauptfenster ──
    root = tk.Tk()
    root.title("SD Model Manager")
    root.geometry("1100x750")
    root.configure(bg="#1e1e2e")

    COLORS = {
        "bg":       "#1e1e2e",
        "surface":  "#313244",
        "border":   "#45475a",
        "text":     "#cdd6f4",
        "subtext":  "#a6adc8",
        "green":    "#a6e3a1",
        "yellow":   "#f9e2af",
        "red":      "#f38ba8",
        "blue":     "#89b4fa",
        "mauve":    "#cba6f7",
        "teal":     "#94e2d5",
    }

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("TLabel",
        background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.configure("Header.TLabel",
        background=COLORS["bg"], foreground=COLORS["mauve"],
        font=("Segoe UI", 13, "bold"))
    style.configure("Sub.TLabel",
        background=COLORS["surface"], foreground=COLORS["subtext"], font=("Segoe UI", 9))
    style.configure("TButton",
        background=COLORS["surface"], foreground=COLORS["text"],
        font=("Segoe UI", 10), borderwidth=0, relief="flat", padding=6)
    style.map("TButton",
        background=[("active", COLORS["border"]), ("pressed", COLORS["border"])])
    style.configure("Accent.TButton",
        background=COLORS["blue"], foreground=COLORS["bg"],
        font=("Segoe UI", 10, "bold"), padding=8)
    style.map("Accent.TButton",
        background=[("active", COLORS["teal"])])
    style.configure("TCheckbutton",
        background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.map("TCheckbutton", background=[("active", COLORS["surface"])])
    style.configure("Treeview",
        background=COLORS["surface"], foreground=COLORS["text"],
        fieldbackground=COLORS["surface"], rowheight=28,
        font=("Segoe UI", 10))
    style.configure("Treeview.Heading",
        background=COLORS["border"], foreground=COLORS["text"],
        font=("Segoe UI", 10, "bold"))
    style.configure("TNotebook", background=COLORS["bg"], tabmargins=0)
    style.configure("TNotebook.Tab",
        background=COLORS["surface"], foreground=COLORS["subtext"],
        font=("Segoe UI", 10), padding=[12, 6])
    style.map("TNotebook.Tab",
        background=[("selected", COLORS["bg"])],
        foreground=[("selected", COLORS["mauve"])])
    style.configure("TSeparator", background=COLORS["border"])
    style.configure("TScrollbar", background=COLORS["surface"], troughcolor=COLORS["bg"])

    # ── Layout ──
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # ── Tab 1: Profile ──
    tab_profiles = ttk.Frame(notebook)
    notebook.add(tab_profiles, text=" Profile ")

    # Header
    hdr = ttk.Frame(tab_profiles)
    hdr.pack(fill="x", padx=10, pady=(10, 5))
    ttk.Label(hdr, text="WebUI Profile", style="Header.TLabel").pack(side="left")

    dry_run_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(hdr, text="Dry-Run (Vorschau)", variable=dry_run_var).pack(side="right", padx=5)

    all_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(hdr, text="Auch deaktivierte", variable=all_var).pack(side="right", padx=5)

    # Profil-Liste
    list_frame = ttk.Frame(tab_profiles, style="Surface.TFrame")
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)

    tree = ttk.Treeview(
        list_frame,
        columns=("name", "package", "rules", "status"),
        show="headings",
        selectmode="browse",
    )
    tree.heading("name",    text="WebUI")
    tree.heading("package", text="Paketordner")
    tree.heading("rules",   text="Regeln")
    tree.heading("status",  text="Status")
    tree.column("name",    width=200)
    tree.column("package", width=280)
    tree.column("rules",   width=60,  anchor="center")
    tree.column("status",  width=120, anchor="center")

    tree.tag_configure("enabled",  foreground=COLORS["text"])
    tree.tag_configure("disabled", foreground=COLORS["subtext"])

    vsb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)

    def refresh_profile_list():
        tree.delete(*tree.get_children())
        for key, p in sorted(profiles.items()):
            pkg_path = get_packages_root() / p.package_folder
            exists = "Gefunden" if pkg_path.exists() else "Nicht gefunden"
            tag = "enabled" if p.enabled else "disabled"
            status_text = f"{'✓' if p.enabled else '○'} {exists}"
            tree.insert("", "end", iid=key, values=(
                p.display_name, p.package_folder, len(p.rules), status_text
            ), tags=(tag,))

    refresh_profile_list()

    # Buttons
    btn_frame = ttk.Frame(tab_profiles)
    btn_frame.pack(fill="x", padx=10, pady=5)

    selected_profile_log = {}

    def apply_selected():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Hinweis", "Kein Profil ausgewaehlt.")
            return
        key = sel[0]
        profile = profiles[key]
        dry = dry_run_var.get()
        _run_apply([profile], dry)

    def apply_all_enabled():
        ps = [p for p in profiles.values() if p.enabled or all_var.get()]
        _run_apply(ps, dry_run_var.get())

    def _run_apply(ps: list, dry: bool):
        log_text.config(state="normal")
        log_text.delete("1.0", "end")
        log_text.insert("end", f"{'='*50}\n")
        log_text.insert("end", f"  Starte Anwendung von {len(ps)} Profil(en)\n")
        log_text.insert("end", f"  Dry-Run: {dry}\n")
        log_text.insert("end", f"{'='*50}\n\n")
        log_text.config(state="disabled")
        notebook.select(tab_log)

        def worker():
            packages_root = get_packages_root()
            for profile in ps:
                _log(f"\n>> {profile.display_name}\n", COLORS["mauve"])
                results = apply_profile(profile, packages_root, dry_run=dry)
                for status, msg in results:
                    color = {
                        "ok":    COLORS["green"],
                        "skip":  COLORS["subtext"],
                        "warn":  COLORS["yellow"],
                        "error": COLORS["red"],
                        "dry":   COLORS["teal"],
                    }.get(status, COLORS["text"])
                    symbol = {"ok": "✓", "skip": "─", "warn": "!", "error": "✗", "dry": "~"}.get(status, "?")
                    _log(f"  {symbol} {msg}\n", color)
            _log(f"\n{'='*50}\n  Fertig!\n{'='*50}\n", COLORS["blue"])

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(btn_frame, text="  ▶  Ausgewaehltes Profil anwenden",
               command=apply_selected).pack(side="left", padx=3)
    ttk.Button(btn_frame, text="  ▶▶  Alle aktiven Profile anwenden",
               command=apply_all_enabled, style="Accent.TButton").pack(side="left", padx=3)
    ttk.Button(btn_frame, text="  ⟳  Neu laden",
               command=lambda: [reload_all(), refresh_profile_list()]).pack(side="right", padx=3)

    # ── Tab 2: Profil-Editor ──
    tab_editor = ttk.Frame(notebook)
    notebook.add(tab_editor, text=" Profil bearbeiten ")

    editor_hdr = ttk.Frame(tab_editor)
    editor_hdr.pack(fill="x", padx=10, pady=(10, 5))
    ttk.Label(editor_hdr, text="Profil-Editor (JSON)", style="Header.TLabel").pack(side="left")

    # Profil-Auswahl
    sel_frame = ttk.Frame(tab_editor)
    sel_frame.pack(fill="x", padx=10, pady=3)
    ttk.Label(sel_frame, text="Profil: ").pack(side="left")
    profile_var = tk.StringVar()
    profile_combo = ttk.Combobox(sel_frame, textvariable=profile_var, state="readonly", width=30)
    profile_combo["values"] = sorted(profiles.keys())
    profile_combo.pack(side="left", padx=5)

    editor_text = scrolledtext.ScrolledText(
        tab_editor, font=("Cascadia Code", 10),
        bg=COLORS["surface"], fg=COLORS["text"],
        insertbackground=COLORS["text"],
        selectbackground=COLORS["border"],
        relief="flat", padx=10, pady=10
    )
    editor_text.pack(fill="both", expand=True, padx=10, pady=5)

    def load_profile_to_editor(*_):
        key = profile_var.get()
        if not key:
            return
        f = PROFILES_DIR / f"{key}.json"
        if f.exists():
            editor_text.delete("1.0", "end")
            editor_text.insert("end", f.read_text(encoding="utf-8"))

    def save_profile_from_editor():
        key = profile_var.get()
        if not key:
            messagebox.showwarning("Hinweis", "Kein Profil ausgewaehlt.")
            return
        content = editor_text.get("1.0", "end-1c")
        try:
            json.loads(content)  # Validierung
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON-Fehler", f"Ungueltige JSON:\n{e}")
            return
        f = PROFILES_DIR / f"{key}.json"
        f.write_text(content, encoding="utf-8")
        reload_all()
        profile_combo["values"] = sorted(profiles.keys())
        refresh_profile_list()
        messagebox.showinfo("Gespeichert", f"Profil '{key}' gespeichert.")

    def new_profile():
        key = tk.simpledialog.askstring("Neues Profil", "Profil-Name (ohne .json):")
        if not key:
            return
        template = {
            "name": key,
            "display_name": key,
            "package_folder": key.lower(),
            "enabled": True,
            "description": "",
            "rules": [
                {"source_types": ["StableDiffusion"], "target": "models/checkpoints"},
                {"source_types": ["Lora", "LyCORIS"], "target": "models/loras"},
                {"source_types": ["VAE"],              "target": "models/vae"}
            ]
        }
        f = PROFILES_DIR / f"{key}.json"
        f.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")
        reload_all()
        profile_combo["values"] = sorted(profiles.keys())
        profile_var.set(key)
        load_profile_to_editor()
        refresh_profile_list()

    profile_combo.bind("<<ComboboxSelected>>", load_profile_to_editor)

    ed_btn = ttk.Frame(tab_editor)
    ed_btn.pack(fill="x", padx=10, pady=5)
    ttk.Button(ed_btn, text="  💾  Speichern", command=save_profile_from_editor,
               style="Accent.TButton").pack(side="left", padx=3)
    ttk.Button(ed_btn, text="  +  Neues Profil", command=new_profile).pack(side="left", padx=3)
    ttk.Button(ed_btn, text="  ↻  Neu laden", command=load_profile_to_editor).pack(side="right", padx=3)

    # ── Tab 3: Master-Typen ──
    tab_types = ttk.Frame(notebook)
    notebook.add(tab_types, text=" Master-Typen ")

    ttk.Label(tab_types, text="Master-Typen (aus StabilityMatrix Quellcode)",
              style="Header.TLabel").pack(anchor="w", padx=10, pady=(10, 5))

    types_tree = ttk.Treeview(
        tab_types,
        columns=("key", "folder", "label", "desc", "path_exists"),
        show="headings",
    )
    types_tree.heading("key",         text="Typ-Key")
    types_tree.heading("folder",      text="Master-Ordner")
    types_tree.heading("label",       text="Bezeichnung")
    types_tree.heading("desc",        text="Beschreibung")
    types_tree.heading("path_exists", text="Ordner?")
    types_tree.column("key",         width=160)
    types_tree.column("folder",      width=180)
    types_tree.column("label",       width=180)
    types_tree.column("desc",        width=280)
    types_tree.column("path_exists", width=80, anchor="center")

    types_tree.tag_configure("exists",   foreground=COLORS["green"])
    types_tree.tag_configure("missing",  foreground=COLORS["yellow"])

    for key, mt in sorted(master_types.items()):
        exists = mt.full_path.exists()
        tag = "exists" if exists else "missing"
        types_tree.insert("", "end", values=(
            key, mt.folder, mt.label, mt.description, "✓" if exists else "─"
        ), tags=(tag,))

    tsb = ttk.Scrollbar(tab_types, orient="vertical", command=types_tree.yview)
    types_tree.configure(yscrollcommand=tsb.set)
    tsb.pack(side="right", fill="y")
    types_tree.pack(fill="both", expand=True, padx=10, pady=5)

    ttk.Label(tab_types,
        text=f"Master-Root: {master_root}",
        style="Sub.TLabel", background=COLORS["bg"]
    ).pack(anchor="w", padx=10, pady=3)

    # ── Tab 4: Log ──
    tab_log = ttk.Frame(notebook)
    notebook.add(tab_log, text=" Log ")

    log_text = scrolledtext.ScrolledText(
        tab_log, font=("Cascadia Code", 10),
        bg=COLORS["surface"], fg=COLORS["text"],
        insertbackground=COLORS["text"],
        state="disabled", relief="flat", padx=10, pady=10
    )
    log_text.pack(fill="both", expand=True, padx=10, pady=10)

    for color_name, color_val in COLORS.items():
        log_text.tag_configure(f"c_{color_name}", foreground=color_val)

    def _log(msg: str, color: str = None):
        def _do():
            log_text.config(state="normal")
            if color:
                tag = f"c_{color}"
                log_text.tag_configure(tag, foreground=color)
                log_text.insert("end", msg, tag)
            else:
                log_text.insert("end", msg)
            log_text.see("end")
            log_text.config(state="disabled")
        root.after(0, _do)

    ttk.Button(tab_log, text="  🗑  Log leeren",
               command=lambda: [log_text.config(state="normal"),
                                log_text.delete("1.0", "end"),
                                log_text.config(state="disabled")]
               ).pack(anchor="e", padx=10, pady=5)

    # ── Statusleiste ──
    status_bar = ttk.Label(
        root,
        text=f"  Master: {master_root}  |  Profile: {len(profiles)}  |  Typen: {len(master_types)}",
        foreground=COLORS["subtext"], background=COLORS["border"],
        font=("Segoe UI", 9)
    )
    status_bar.pack(fill="x", side="bottom")

    # Simpledialog importieren
    import tkinter.simpledialog

    root.mainloop()


# ─────────────────────────── Einstiegspunkt ──────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SD Model Manager - Erstellt Symlinks/Junctions fuer WebUI-Modellordner"
    )
    parser.add_argument("--cli",      action="store_true", help="CLI-Modus (kein GUI)")
    parser.add_argument("--dry-run",  action="store_true", help="Keine echten Aenderungen")
    parser.add_argument("--profile",  nargs="+",           help="Nur bestimmte Profile anwenden")
    parser.add_argument("--all",      action="store_true", help="Auch deaktivierte Profile")
    parser.add_argument("--verbose",  action="store_true", help="Ausfuehrliche Ausgabe")
    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        run_gui()
