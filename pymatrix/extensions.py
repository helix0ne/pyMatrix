"""
PyMatrix Extension Manager
Verwaltet ComfyUI Custom Nodes und A1111/Forge Extensions.
Speziell: ComfyUI-Lora-Manager von willmiao.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# Callback: progress_cb(step: str, percent: float, message: str)
ProgressCallback = Callable[[str, float, str], None]


# ── Bekannte Extension-Katalog ────────────────────────────────────────

@dataclass
class ExtensionDef:
    id: str
    display_name: str
    description: str
    github_repo: str          # "user/repo"
    branch: str = "main"
    category: str = "general"  # "comfyui" | "a1111" | "forge" | "general"
    tags: list[str] = field(default_factory=list)
    homepage: str = ""
    install_notes: str = ""
    featured: bool = False    # In der UI hervorheben


# ComfyUI Custom Nodes Katalog
COMFYUI_NODES_CATALOG: dict[str, ExtensionDef] = {
    "ComfyUI-Lora-Manager": ExtensionDef(
        id="ComfyUI-Lora-Manager",
        display_name="ComfyUI LoRA Manager",
        description=(
            "Vollstaendiger LoRA Manager fuer ComfyUI: Vorschau-Thumbnails, "
            "Aktivierungs-Tags, Ordner-Browsen, CivitAI-Metadaten-Sync, "
            "Top-Picks Sidebar und mehr."
        ),
        github_repo="willmiao/ComfyUI-Lora-Manager",
        branch="main",
        category="comfyui",
        tags=["lora", "management", "civitai", "featured"],
        homepage="https://github.com/willmiao/ComfyUI-Lora-Manager",
        install_notes="Nach Installation ComfyUI neu starten. LoRA-Verzeichnis in den Node-Einstellungen konfigurieren.",
        featured=True,
    ),
    "ComfyUI-Manager": ExtensionDef(
        id="ComfyUI-Manager",
        display_name="ComfyUI Manager",
        description="Installiert und verwaltet ComfyUI Custom Nodes per GUI.",
        github_repo="ltdrdata/ComfyUI-Manager",
        branch="main",
        category="comfyui",
        tags=["management", "essential"],
        homepage="https://github.com/ltdrdata/ComfyUI-Manager",
        featured=True,
    ),
    "ComfyUI-Impact-Pack": ExtensionDef(
        id="ComfyUI-Impact-Pack",
        display_name="Impact Pack",
        description="Detailer, ADetailer-aehnliche Funktionen, Segmentation, Wildcards.",
        github_repo="ltdrdata/ComfyUI-Impact-Pack",
        branch="Main",
        category="comfyui",
        tags=["detailer", "segmentation", "upscale"],
        homepage="https://github.com/ltdrdata/ComfyUI-Impact-Pack",
        featured=True,
    ),
    "ComfyUI_IPAdapter_plus": ExtensionDef(
        id="ComfyUI_IPAdapter_plus",
        display_name="IPAdapter Plus",
        description="IP-Adapter Nodes: Style Transfer, Face ID, Face Swap.",
        github_repo="cubiq/ComfyUI_IPAdapter_plus",
        branch="main",
        category="comfyui",
        tags=["ipadapter", "style", "face"],
        homepage="https://github.com/cubiq/ComfyUI_IPAdapter_plus",
    ),
    "ComfyUI-ControlNet-Aux": ExtensionDef(
        id="ComfyUI-ControlNet-Aux",
        display_name="ControlNet Auxiliary Preprocessors",
        description="Preprocessoren fuer ControlNet: Canny, Depth, Openpose, etc.",
        github_repo="Fannovel16/comfyui_controlnet_aux",
        branch="main",
        category="comfyui",
        tags=["controlnet", "preprocessor"],
        homepage="https://github.com/Fannovel16/comfyui_controlnet_aux",
    ),
    "was-node-suite-comfyui": ExtensionDef(
        id="was-node-suite-comfyui",
        display_name="WAS Node Suite",
        description="Umfangreiche Node-Sammlung: Image Processing, Math, Logic, Text.",
        github_repo="WASasquatch/was-node-suite-comfyui",
        branch="main",
        category="comfyui",
        tags=["utility", "image", "text"],
        homepage="https://github.com/WASasquatch/was-node-suite-comfyui",
    ),
    "ComfyUI-Easy-Use": ExtensionDef(
        id="ComfyUI-Easy-Use",
        display_name="Easy Use",
        description="Vereinfachte All-in-One Nodes fuer schnelle Workflows.",
        github_repo="yolain/ComfyUI-Easy-Use",
        branch="main",
        category="comfyui",
        tags=["workflow", "simplified"],
        homepage="https://github.com/yolain/ComfyUI-Easy-Use",
    ),
    "ComfyUI-GGUF": ExtensionDef(
        id="ComfyUI-GGUF",
        display_name="GGUF Loader",
        description="Laedt quantisierte GGUF-Modelle (Flux, SD etc.) in ComfyUI.",
        github_repo="city96/ComfyUI-GGUF",
        branch="main",
        category="comfyui",
        tags=["gguf", "quantized", "flux"],
        homepage="https://github.com/city96/ComfyUI-GGUF",
    ),
    "ComfyUI_essentials": ExtensionDef(
        id="ComfyUI_essentials",
        display_name="Essentials",
        description="Nuetzliche Nodes die in ComfyUI fehlen: Masken, Image Tools, etc.",
        github_repo="cubiq/ComfyUI_essentials",
        branch="main",
        category="comfyui",
        tags=["utility", "mask", "image"],
        homepage="https://github.com/cubiq/ComfyUI_essentials",
    ),
    "ComfyUI-Advanced-ControlNet": ExtensionDef(
        id="ComfyUI-Advanced-ControlNet",
        display_name="Advanced ControlNet",
        description="Erweiterte ControlNet-Steuerung mit Scheduling und mehr.",
        github_repo="Kosinkadink/ComfyUI-Advanced-ControlNet",
        branch="main",
        category="comfyui",
        tags=["controlnet", "advanced"],
        homepage="https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet",
    ),
    "rgthree-comfy": ExtensionDef(
        id="rgthree-comfy",
        display_name="rgthree Nodes",
        description="Context Nodes, Power-Lora-Loader, Bookmark-Knoten und mehr.",
        github_repo="rgthree/rgthree-comfy",
        branch="main",
        category="comfyui",
        tags=["utility", "lora", "context"],
        homepage="https://github.com/rgthree/rgthree-comfy",
    ),
    "ComfyUI-Florence2": ExtensionDef(
        id="ComfyUI-Florence2",
        display_name="Florence-2 Nodes",
        description="Microsofts Florence-2 Vision Model: Captioning, Segmentation.",
        github_repo="kijai/ComfyUI-Florence2",
        branch="main",
        category="comfyui",
        tags=["vision", "captioning", "segmentation"],
        homepage="https://github.com/kijai/ComfyUI-Florence2",
    ),
}

# A1111 / Forge Extensions Katalog
A1111_EXTENSIONS_CATALOG: dict[str, ExtensionDef] = {
    "adetailer": ExtensionDef(
        id="adetailer",
        display_name="ADetailer",
        description="Automatische Gesichts- und Koerper-Nachbearbeitung mit Inpainting.",
        github_repo="Bing-su/adetailer",
        branch="main",
        category="a1111",
        tags=["detailer", "face", "inpainting"],
        homepage="https://github.com/Bing-su/adetailer",
        featured=True,
    ),
    "sd-webui-controlnet": ExtensionDef(
        id="sd-webui-controlnet",
        display_name="ControlNet",
        description="ControlNet fuer A1111/Forge — Pose, Depth, Canny, etc.",
        github_repo="Mikubill/sd-webui-controlnet",
        branch="main",
        category="a1111",
        tags=["controlnet"],
        homepage="https://github.com/Mikubill/sd-webui-controlnet",
        featured=True,
    ),
    "sd-webui-regional-prompter": ExtensionDef(
        id="sd-webui-regional-prompter",
        display_name="Regional Prompter",
        description="Verschiedene Prompts fuer verschiedene Bildbereiche.",
        github_repo="hako-mikan/sd-webui-regional-prompter",
        branch="main",
        category="a1111",
        tags=["prompt", "regions"],
        homepage="https://github.com/hako-mikan/sd-webui-regional-prompter",
    ),
    "sd-dynamic-prompts": ExtensionDef(
        id="sd-dynamic-prompts",
        display_name="Dynamic Prompts",
        description="Wildcards, zufallige Prompt-Varianten, Jinja2-Templates.",
        github_repo="adieyal/sd-dynamic-prompts",
        branch="main",
        category="a1111",
        tags=["prompt", "wildcard"],
        homepage="https://github.com/adieyal/sd-dynamic-prompts",
    ),
    "multidiffusion-upscaler-for-automatic1111": ExtensionDef(
        id="multidiffusion-upscaler-for-automatic1111",
        display_name="MultiDiffusion / Tiled VAE",
        description="Tiled Diffusion und Tiled VAE fuer grosse Bilder mit wenig VRAM.",
        github_repo="pkuliyi2015/multidiffusion-upscaler-for-automatic1111",
        branch="main",
        category="a1111",
        tags=["upscale", "tiled", "vram"],
        homepage="https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111",
    ),
    "sd-webui-animatediff": ExtensionDef(
        id="sd-webui-animatediff",
        display_name="AnimateDiff",
        description="Video / Animation direkt in A1111 generieren.",
        github_repo="continue-revolution/sd-webui-animatediff",
        branch="main",
        category="a1111",
        tags=["animation", "video"],
        homepage="https://github.com/continue-revolution/sd-webui-animatediff",
    ),
}


@dataclass
class InstalledExtension:
    ext_def: ExtensionDef
    install_path: Path
    is_enabled: bool = True
    installed_sha: str = ""
    update_available: bool = False


class ExtensionManager:
    """Verwaltet ComfyUI Custom Nodes und A1111 Extensions."""

    def __init__(self, packages_root: Path):
        self.packages_root = packages_root

    # ── Scan installierter Extensions ────────────────────────

    def scan_comfyui_nodes(self, comfyui_path: Path) -> list[InstalledExtension]:
        """Scannt alle installierten ComfyUI Custom Nodes."""
        nodes_dir = comfyui_path / "custom_nodes"
        if not nodes_dir.exists():
            return []

        installed = []
        for d in sorted(nodes_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("__"):
                continue
            ext_def = COMFYUI_NODES_CATALOG.get(d.name)
            if ext_def is None:
                # Unbekannte Extension erstellen
                ext_def = ExtensionDef(
                    id=d.name,
                    display_name=d.name,
                    description="Installierte Extension (nicht im Katalog)",
                    github_repo="",
                    category="comfyui",
                )
            sha = self._read_installed_sha(d)
            installed.append(InstalledExtension(
                ext_def=ext_def,
                install_path=d,
                is_enabled=not (d / ".disabled").exists(),
                installed_sha=sha,
            ))
        return installed

    def scan_a1111_extensions(self, webui_path: Path) -> list[InstalledExtension]:
        """Scannt alle installierten A1111/Forge Extensions."""
        ext_dir = webui_path / "extensions"
        if not ext_dir.exists():
            return []

        installed = []
        for d in sorted(ext_dir.iterdir()):
            if not d.is_dir():
                continue
            ext_def = A1111_EXTENSIONS_CATALOG.get(d.name)
            if ext_def is None:
                ext_def = ExtensionDef(
                    id=d.name,
                    display_name=d.name,
                    description="Installierte Extension (nicht im Katalog)",
                    github_repo="",
                    category="a1111",
                )
            sha = self._read_installed_sha(d)
            installed.append(InstalledExtension(
                ext_def=ext_def,
                install_path=d,
                is_enabled=True,
                installed_sha=sha,
            ))
        return installed

    # ── Installation ─────────────────────────────────────────

    def install_comfyui_node(self, ext_def: ExtensionDef, comfyui_path: Path,
                              progress_cb: ProgressCallback = None,
                              done_cb: Callable[[bool, str], None] = None) -> threading.Thread:
        """Installiert einen ComfyUI Custom Node via git clone."""
        def _run():
            target = comfyui_path / "custom_nodes" / ext_def.id
            ok, msg = self._git_clone(ext_def.github_repo, ext_def.branch,
                                       target, progress_cb)
            if ok and (target / "requirements.txt").exists():
                self._pip_install_requirements(
                    comfyui_path / ".venv", target / "requirements.txt", progress_cb
                )
            if done_cb:
                done_cb(ok, msg)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def install_a1111_extension(self, ext_def: ExtensionDef, webui_path: Path,
                                  progress_cb: ProgressCallback = None,
                                  done_cb: Callable[[bool, str], None] = None) -> threading.Thread:
        """Installiert eine A1111 Extension via git clone."""
        def _run():
            target = webui_path / "extensions" / ext_def.id
            ok, msg = self._git_clone(ext_def.github_repo, ext_def.branch,
                                       target, progress_cb)
            if done_cb:
                done_cb(ok, msg)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def update_extension(self, ext: InstalledExtension,
                          progress_cb: ProgressCallback = None,
                          done_cb: Callable[[bool, str], None] = None) -> threading.Thread:
        """Aktualisiert eine installierte Extension via git pull."""
        def _run():
            ok, msg = self._git_pull(ext.install_path, progress_cb)
            if done_cb:
                done_cb(ok, msg)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def uninstall_extension(self, ext: InstalledExtension) -> bool:
        """Entfernt eine Extension vom Dateisystem."""
        try:
            shutil.rmtree(ext.install_path)
            return True
        except OSError:
            return False

    def toggle_extension(self, ext: InstalledExtension) -> bool:
        """Aktiviert / Deaktiviert eine Extension (nur ComfyUI via .disabled-Marker)."""
        disabled_marker = ext.install_path / ".disabled"
        if ext.is_enabled:
            try:
                disabled_marker.touch()
                ext.is_enabled = False
                return True
            except OSError:
                return False
        else:
            try:
                disabled_marker.unlink(missing_ok=True)
                ext.is_enabled = True
                return True
            except OSError:
                return False

    def check_updates(self, extensions: list[InstalledExtension],
                       progress_cb: ProgressCallback = None) -> list[InstalledExtension]:
        """Prueft welche Extensions Updates haben. Gibt aktualisierte Liste zurueck."""
        for i, ext in enumerate(extensions):
            if not ext.ext_def.github_repo:
                continue
            if progress_cb:
                pct = (i / len(extensions)) * 100
                progress_cb("check", pct, f"Pruefe {ext.ext_def.display_name}...")

            latest_sha = self._get_remote_sha(ext.install_path)
            if latest_sha and latest_sha != ext.installed_sha:
                ext.update_available = True

        return extensions

    # ── Git-Operationen ──────────────────────────────────────

    def _git_clone(self, repo: str, branch: str, target: Path,
                   progress_cb: ProgressCallback) -> tuple[bool, str]:
        """Klont ein GitHub-Repo."""
        if target.exists():
            return False, f"Verzeichnis existiert bereits: {target.name}"

        if progress_cb:
            progress_cb("clone", 0, f"Klone {repo}...")

        url = f"https://github.com/{repo}.git"
        git = self._find_git()
        if not git:
            return False, "Git nicht gefunden! Bitte Git installieren."

        try:
            proc = subprocess.run(
                [git, "clone", "--depth=1", "--branch", branch, url, str(target)],
                capture_output=True, text=True, timeout=300
            )
            if proc.returncode != 0:
                return False, proc.stderr.strip()[:300] or proc.stdout.strip()[:300]

            if progress_cb:
                progress_cb("clone", 100, "Clone abgeschlossen!")
            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Git clone Timeout (>5 Min)"
        except Exception as e:
            return False, str(e)

    def _git_pull(self, path: Path,
                  progress_cb: ProgressCallback) -> tuple[bool, str]:
        """Fuehrt git pull im angegebenen Verzeichnis aus."""
        if not path.exists():
            return False, "Verzeichnis nicht gefunden"

        git = self._find_git()
        if not git:
            return False, "Git nicht gefunden"

        if progress_cb:
            progress_cb("pull", 0, f"Aktualisiere {path.name}...")

        try:
            proc = subprocess.run(
                [git, "pull", "--ff-only"],
                cwd=str(path), capture_output=True, text=True, timeout=120
            )
            if proc.returncode != 0:
                return False, proc.stderr.strip()[:300]
            if progress_cb:
                progress_cb("pull", 100, "Update abgeschlossen!")
            return True, proc.stdout.strip()
        except Exception as e:
            return False, str(e)

    def _get_remote_sha(self, path: Path) -> str:
        """Liest den aktuellen Remote-SHA via git."""
        git = self._find_git()
        if not git or not path.exists():
            return ""
        try:
            proc = subprocess.run(
                [git, "rev-parse", "--short", "HEAD"],
                cwd=str(path), capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception:
            pass
        return ""

    def _read_installed_sha(self, path: Path) -> str:
        """Liest HEAD SHA aus .git/refs oder via git rev-parse."""
        head_file = path / ".git" / "HEAD"
        if head_file.exists():
            return self._get_remote_sha(path)
        return ""

    def _find_git(self) -> Optional[str]:
        """Sucht git Executable."""
        candidates = ["git", "git.exe"]
        # Pruefen ob git im PATH ist
        for name in candidates:
            result = shutil.which(name)
            if result:
                return result
        # Windows: Typische Installationspfade
        win_paths = [
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files (x86)\Git\bin\git.exe",
        ]
        for p in win_paths:
            if os.path.exists(p):
                return p
        return None

    def _pip_install_requirements(self, venv_path: Path, req_file: Path,
                                   progress_cb: ProgressCallback) -> None:
        """Installiert Requirements einer Extension."""
        pip = venv_path / "Scripts" / "pip.exe"
        if not pip.exists():
            pip = venv_path / "bin" / "pip"
        if not pip.exists():
            return

        if progress_cb:
            progress_cb("pip", 90, f"Installiere Abhaengigkeiten...")
        try:
            subprocess.run(
                [str(pip), "install", "-r", str(req_file), "--quiet"],
                check=True, capture_output=True, text=True, timeout=300
            )
        except Exception:
            pass
