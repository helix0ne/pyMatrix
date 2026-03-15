"""
PyMatrix Core — Liest/Schreibt StabilityMatrix settings.json,
verwaltet Paket-Starts/-Stopps, liest Modell-Bibliothek.
"""

import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

# ── Standard StabilityMatrix-Pfad ──────────────────────────
DEFAULT_SM_ROOT = Path("D:/Programme/stability_matrix")

# ── Bekannte Pakete: GitHub-Repos + Start-Script ──────────
KNOWN_PACKAGES = {
    "stable-diffusion-webui": {
        "display": "AUTOMATIC1111 WebUI",
        "repo": "AUTOMATIC1111/stable-diffusion-webui",
        "launch": "launch.py",
        "color": "#89b4fa",
        "icon": "\u25A0",
    },
    "stable-diffusion-webui-forge": {
        "display": "SD WebUI Forge",
        "repo": "lllyasviel/stable-diffusion-webui-forge",
        "launch": "launch.py",
        "color": "#fab387",
        "icon": "\u25B6",
    },
    "forge-neo": {
        "display": "Forge Neo",
        "repo": "Haoming02/sd-webui-forge-classic",
        "launch": "launch.py",
        "color": "#f38ba8",
        "icon": "\u25B6",
    },
    "reforge": {
        "display": "SD WebUI reForge",
        "repo": "Panchovix/stable-diffusion-webui-reForge",
        "launch": "launch.py",
        "color": "#cba6f7",
        "icon": "\u25B6",
    },
    "forge-classic": {
        "display": "ForgeClassic",
        "repo": "Haoming02/sd-webui-forge-classic",
        "launch": "launch.py",
        "color": "#89dceb",
        "icon": "\u25B6",
    },
    "ComfyUI": {
        "display": "ComfyUI",
        "repo": "comfyanonymous/ComfyUI",
        "launch": "main.py",
        "color": "#a6e3a1",
        "icon": "\u25C6",
    },
    "stable-diffusion-webui-directml": {
        "display": "A1111 DirectML",
        "repo": "lshqqytiger/stable-diffusion-webui-directml",
        "launch": "launch.py",
        "color": "#f9e2af",
        "icon": "\u25A0",
    },
    "InvokeAI": {
        "display": "InvokeAI",
        "repo": "invoke-ai/InvokeAI",
        "launch": "invokeai-web",
        "color": "#94e2d5",
        "icon": "\u25C6",
    },
    "stable-diffusion-webui-ux": {
        "display": "SD WebUI UX",
        "repo": "anapnoe/stable-diffusion-webui-ux",
        "launch": "launch.py",
        "color": "#b4befe",
        "icon": "\u25A0",
    },
    "SD.Next": {
        "display": "SD.Next (vladmandic)",
        "repo": "vladmandic/automatic",
        "launch": "launch.py",
        "color": "#f2cdcd",
        "icon": "\u25B6",
    },
    "Fooocus": {
        "display": "Fooocus",
        "repo": "lllyasviel/Fooocus",
        "launch": "launch.py",
        "color": "#cba6f7",
        "icon": "\u25C6",
    },
    "kohya_ss": {
        "display": "Kohya GUI",
        "repo": "bmaltais/kohya_ss",
        "launch": "kohya_gui.py",
        "color": "#94e2d5",
        "icon": "\u2699",
    },
}


@dataclass
class LaunchArg:
    name: str
    arg_type: str  # "Bool" | "String" | "OptionFlag"
    value: object  # bool or str


@dataclass
class Package:
    id: str
    display_name: str
    package_name: str  # e.g. "ComfyUI"
    library_path: str  # relative to SM root, e.g. "Packages\\ComfyUI"
    launch_command: str
    launch_args: list[LaunchArg]
    version_branch: str = "main"
    version_sha: str = ""
    python_version: str = "3.10.11"
    preferred_shared_folder: str = "Symlink"
    use_shared_output: bool = False
    process: Optional[object] = None  # subprocess.Popen

    @property
    def abs_path(self) -> Path:
        """Absoluter Pfad zum Paketordner."""
        sm_root = PyMatrixConfig.instance().sm_root if PyMatrixConfig._instance else DEFAULT_SM_ROOT
        return sm_root / self.library_path

    @property
    def is_installed(self) -> bool:
        return self.abs_path.exists()

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def color(self) -> str:
        info = KNOWN_PACKAGES.get(self.package_name, {})
        return info.get("color", "#89b4fa")

    @property
    def icon(self) -> str:
        info = KNOWN_PACKAGES.get(self.package_name, {})
        return info.get("icon", "\u25A0")

    def build_launch_cmdline(self, python_path: Path) -> list[str]:
        """Baut die vollstaendige Kommandozeile zum Starten des Pakets."""
        cmd = [str(python_path), self.launch_command]
        for arg in self.launch_args:
            if arg.arg_type == "Bool" and arg.value:
                if arg.name:
                    cmd.append(arg.name)
            elif arg.arg_type in ("String", "OptionString") and arg.value:
                val = str(arg.value).strip()
                if val:
                    if arg.name:
                        cmd.extend([arg.name, val])
                    else:
                        # Extra args ohne Name (z.B. "--xformers --ckpt-dir ...")
                        cmd.extend(val.split())
        return cmd


class PyMatrixConfig:
    """Singleton-Konfiguration fuer PyMatrix."""
    _instance: Optional["PyMatrixConfig"] = None

    def __init__(self, sm_root: Path = DEFAULT_SM_ROOT):
        self.sm_root = sm_root
        self.packages: list[Package] = []
        self.settings: dict = {}
        PyMatrixConfig._instance = self

    @classmethod
    def instance(cls) -> "PyMatrixConfig":
        if cls._instance is None:
            cls._instance = PyMatrixConfig()
        return cls._instance

    @property
    def settings_path(self) -> Path:
        return self.sm_root / "settings.json"

    @property
    def models_root(self) -> Path:
        return self.sm_root / "models"

    @property
    def packages_root(self) -> Path:
        return self.sm_root / "Packages"

    def load(self) -> None:
        """Laedt settings.json und parst alle Pakete."""
        if not self.settings_path.exists():
            self.packages = []
            return

        with open(self.settings_path, "r", encoding="utf-8") as f:
            self.settings = json.load(f)

        self.packages = []
        for pkg_data in self.settings.get("InstalledPackages", []):
            args = []
            for a in pkg_data.get("LaunchArgs", []):
                args.append(LaunchArg(
                    name=a.get("Name", ""),
                    arg_type=a.get("Type", "String"),
                    value=a.get("OptionValue", ""),
                ))

            ver = pkg_data.get("Version", {})
            pkg = Package(
                id=pkg_data.get("Id", ""),
                display_name=pkg_data.get("DisplayName", ""),
                package_name=pkg_data.get("PackageName", ""),
                library_path=pkg_data.get("LibraryPath", ""),
                launch_command=pkg_data.get("LaunchCommand", "launch.py"),
                launch_args=args,
                version_branch=ver.get("InstalledBranch", "main"),
                version_sha=ver.get("InstalledCommitSha", "")[:8],
                python_version=pkg_data.get("PythonVersion", ""),
                preferred_shared_folder=pkg_data.get("PreferredSharedFolderMethod", "Symlink"),
                use_shared_output=pkg_data.get("UseSharedOutputFolder", False),
            )
            self.packages.append(pkg)

    def save_launch_args(self, package_id: str, args: list[LaunchArg]) -> None:
        """Speichert Launch-Args zurueck in settings.json."""
        if not self.settings_path.exists():
            return
        for pkg_data in self.settings.get("InstalledPackages", []):
            if pkg_data.get("Id") == package_id:
                pkg_data["LaunchArgs"] = [
                    {"Name": a.name, "Type": a.arg_type, "OptionValue": a.value}
                    for a in args
                ]
                break
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def find_python(self, pkg: Package) -> Optional[Path]:
        """Findet den Python-Interpreter fuer ein Paket."""
        candidates = [
            # SM eigenes Python (portabel)
            self.sm_root / "PortableGit" / "bin" / "python.exe",
            pkg.abs_path / ".venv" / "Scripts" / "python.exe",
            pkg.abs_path / "venv" / "Scripts" / "python.exe",
            pkg.abs_path / ".venv" / "bin" / "python",
            # System Python
            Path(sys.executable),
        ]
        # SM Python-Ordner suchen
        py_dir = self.sm_root / "PyEnv"
        if py_dir.exists():
            for d in py_dir.iterdir():
                if d.is_dir() and pkg.python_version in d.name:
                    p = d / "python.exe"
                    if p.exists():
                        candidates.insert(0, p)

        for c in candidates:
            if c.exists():
                return c
        return Path(sys.executable)


class PackageLauncher:
    """Startet und stoppt WebUI-Pakete."""

    def __init__(self, config: PyMatrixConfig):
        self.config = config
        self._processes: dict[str, subprocess.Popen] = {}
        self.on_output: Optional[Callable[[str, str, str], None]] = None
        # id -> log_callback(pkg_id, line, level)

    def start(self, pkg: Package, extra_args: list[str] = None,
              output_cb: Callable = None) -> bool:
        if self.is_running(pkg.id):
            return False

        python = self.config.find_python(pkg)
        cmd = pkg.build_launch_cmdline(python)
        if extra_args:
            cmd.extend(extra_args)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(pkg.abs_path)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(pkg.abs_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
            )
            self._processes[pkg.id] = proc
            pkg.process = proc

            # Hintergrundthread fuer Output lesen
            def read_output():
                for line in iter(proc.stdout.readline, ""):
                    if output_cb:
                        output_cb(pkg.id, line.rstrip(), "info")
                    elif self.on_output:
                        self.on_output(pkg.id, line.rstrip(), "info")
                proc.wait()
                if output_cb:
                    output_cb(pkg.id, f"[Prozess beendet: RC={proc.returncode}]", "info")

            t = threading.Thread(target=read_output, daemon=True)
            t.start()
            return True
        except Exception as e:
            if output_cb:
                output_cb(pkg.id, f"Startfehler: {e}", "error")
            return False

    def stop(self, pkg_id: str) -> None:
        proc = self._processes.get(pkg_id)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._processes.pop(pkg_id, None)
        for pkg in self.config.packages:
            if pkg.id == pkg_id:
                pkg.process = None
                break

    def stop_all(self) -> None:
        for pkg_id in list(self._processes.keys()):
            self.stop(pkg_id)

    def is_running(self, pkg_id: str) -> bool:
        proc = self._processes.get(pkg_id)
        return proc is not None and proc.poll() is None

    def get_running_ids(self) -> list[str]:
        return [pid for pid, proc in self._processes.items()
                if proc.poll() is None]
