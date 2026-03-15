"""
PyMatrix Installer — Paket-Installation und -Updates
Laedt GitHub-Archive, entpackt, erstellt venv, installiert Requirements.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from packages_catalog import PackageDef, PACKAGE_CATALOG


# ── Fortschritts-Callback-Typen ──────────────────────────────────────
# progress_cb(step: str, percent: float, message: str)
ProgressCallback = Callable[[str, float, str], None]


@dataclass
class InstallResult:
    success: bool
    package_name: str
    install_path: Path
    error: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class UpdateResult:
    success: bool
    package_name: str
    old_sha: str
    new_sha: str
    error: str = ""


def _github_latest_sha(repo: str, branch: str, timeout: int = 10) -> str:
    """Holt den neuesten Commit-SHA eines GitHub-Repos."""
    url = f"https://api.github.com/repos/{repo}/commits/{branch}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
            return data["sha"][:8]
    except Exception:
        return ""


def _github_archive_url(repo: str, branch: str) -> str:
    """Gibt die URL zum ZIP-Archiv eines GitHub-Repos zurueck."""
    return f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"


def _download_file(url: str, dest: Path,
                   progress_cb: ProgressCallback = None,
                   step: str = "download") -> bool:
    """Laedt eine Datei herunter mit Fortschritts-Callback."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PyMatrix/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536  # 64 KB

            with open(dest, "wb") as f:
                while True:
                    data = response.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if progress_cb and total > 0:
                        pct = (downloaded / total) * 100
                        mb_done = downloaded / 1_048_576
                        mb_total = total / 1_048_576
                        progress_cb(step, pct, f"{mb_done:.1f} / {mb_total:.1f} MB")
        return True
    except Exception as e:
        if progress_cb:
            progress_cb(step, -1, f"Download fehlgeschlagen: {e}")
        return False


class PackageInstaller:
    """Installiert und aktualisiert WebUI-Pakete."""

    def __init__(self, sm_root: Path):
        self.sm_root = sm_root
        self.packages_root = sm_root / "Packages"
        self._running: dict[str, threading.Thread] = {}

    # ── Oeffentliche API ─────────────────────────────────────

    def install(self, pkg_def: PackageDef, install_path: Optional[Path] = None,
                progress_cb: ProgressCallback = None,
                done_cb: Callable[[InstallResult], None] = None) -> threading.Thread:
        """Startet die Installation in einem Hintergrundthread."""
        if install_path is None:
            install_path = self.packages_root / pkg_def.name

        def _run():
            result = self._install_sync(pkg_def, install_path, progress_cb)
            if done_cb:
                done_cb(result)
            self._running.pop(pkg_def.name, None)

        t = threading.Thread(target=_run, daemon=True, name=f"install-{pkg_def.name}")
        self._running[pkg_def.name] = t
        t.start()
        return t

    def update(self, pkg_def: PackageDef, install_path: Path,
               current_sha: str = "",
               progress_cb: ProgressCallback = None,
               done_cb: Callable[[UpdateResult], None] = None) -> threading.Thread:
        """Startet das Update in einem Hintergrundthread."""
        def _run():
            result = self._update_sync(pkg_def, install_path, current_sha, progress_cb)
            if done_cb:
                done_cb(result)
            self._running.pop(pkg_def.name, None)

        t = threading.Thread(target=_run, daemon=True, name=f"update-{pkg_def.name}")
        self._running[pkg_def.name] = t
        t.start()
        return t

    def is_busy(self, pkg_name: str) -> bool:
        t = self._running.get(pkg_name)
        return t is not None and t.is_alive()

    def check_update_available(self, pkg_def: PackageDef, current_sha: str) -> bool:
        """Prueft ob ein Update verfuegbar ist (vergleicht SHA)."""
        latest = _github_latest_sha(pkg_def.github_repo, pkg_def.branch)
        if not latest:
            return False
        return latest != current_sha[:8]

    # ── Interne Implementierung ──────────────────────────────

    def _install_sync(self, pkg_def: PackageDef, install_path: Path,
                      progress_cb: ProgressCallback) -> InstallResult:
        warnings = []

        # Schritt 1: Verzeichnis anlegen
        if progress_cb:
            progress_cb("vorbereitung", 0, f"Installiere {pkg_def.display_name}...")

        if install_path.exists():
            return InstallResult(False, pkg_def.name, install_path,
                                 error="Verzeichnis existiert bereits")

        try:
            install_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return InstallResult(False, pkg_def.name, install_path, error=str(e))

        # Schritt 2: Archiv herunterladen
        archive_url = _github_archive_url(pkg_def.github_repo, pkg_def.branch)
        tmp_zip = install_path.parent / f"_{pkg_def.name}_tmp.zip"

        if progress_cb:
            progress_cb("download", 0, f"Lade von GitHub: {pkg_def.github_repo}")

        ok = _download_file(archive_url, tmp_zip, progress_cb, "download")
        if not ok:
            shutil.rmtree(install_path, ignore_errors=True)
            tmp_zip.unlink(missing_ok=True)
            return InstallResult(False, pkg_def.name, install_path,
                                 error="Download fehlgeschlagen")

        # Schritt 3: Entpacken
        if progress_cb:
            progress_cb("entpacken", 90, "Entpacke Archiv...")

        try:
            with zipfile.ZipFile(tmp_zip, "r") as z:
                # GitHub-Archive haben einen Unterordner: repo-branch/
                members = z.namelist()
                prefix = members[0].split("/")[0] + "/" if members else ""

                for member in members:
                    if not member.startswith(prefix):
                        continue
                    rel = member[len(prefix):]
                    if not rel:
                        continue
                    target = install_path / rel
                    if member.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        except Exception as e:
            shutil.rmtree(install_path, ignore_errors=True)
            tmp_zip.unlink(missing_ok=True)
            return InstallResult(False, pkg_def.name, install_path,
                                 error=f"Entpacken fehlgeschlagen: {e}")
        finally:
            tmp_zip.unlink(missing_ok=True)

        # Schritt 4: venv erstellen
        if progress_cb:
            progress_cb("venv", 92, "Erstelle Python Virtual Environment...")

        python_exe = sys.executable
        venv_path = install_path / ".venv"
        try:
            subprocess.run(
                [python_exe, "-m", "venv", str(venv_path)],
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            warnings.append(f"venv konnte nicht erstellt werden: {e.stderr[:200]}")
            venv_path = None

        # Schritt 5: Requirements installieren
        if venv_path and venv_path.exists():
            pip = venv_path / "Scripts" / "pip.exe"
            if not pip.exists():
                pip = venv_path / "bin" / "pip"

            req_file = install_path / pkg_def.pip_requirements
            if req_file.exists() and pip.exists():
                if progress_cb:
                    progress_cb("requirements", 95, "Installiere Python-Pakete...")
                try:
                    subprocess.run(
                        [str(pip), "install", "-r", str(req_file), "--quiet"],
                        check=True, capture_output=True, text=True,
                        timeout=600
                    )
                except subprocess.CalledProcessError as e:
                    warnings.append(f"requirements.txt Fehler: {e.stderr[:300]}")
                except subprocess.TimeoutExpired:
                    warnings.append("pip install Timeout (>10 Min)")

        if progress_cb:
            progress_cb("fertig", 100, f"{pkg_def.display_name} installiert!")

        return InstallResult(
            success=True,
            package_name=pkg_def.name,
            install_path=install_path,
            warnings=warnings,
        )

    def _update_sync(self, pkg_def: PackageDef, install_path: Path,
                     current_sha: str, progress_cb: ProgressCallback) -> UpdateResult:
        if not install_path.exists():
            return UpdateResult(False, pkg_def.name, current_sha, "",
                                error="Paket-Verzeichnis nicht gefunden")

        if progress_cb:
            progress_cb("update", 0, f"Pruefe {pkg_def.display_name}...")

        new_sha = _github_latest_sha(pkg_def.github_repo, pkg_def.branch)
        if not new_sha:
            return UpdateResult(False, pkg_def.name, current_sha, "",
                                error="Konnte SHA nicht abrufen (kein Internet?)")

        if new_sha == current_sha[:8]:
            return UpdateResult(True, pkg_def.name, current_sha, new_sha)

        # Download des neuen Archivs
        archive_url = _github_archive_url(pkg_def.github_repo, pkg_def.branch)
        tmp_zip = install_path.parent / f"_{pkg_def.name}_update.zip"

        if progress_cb:
            progress_cb("download", 5, "Lade Update von GitHub...")

        ok = _download_file(archive_url, tmp_zip, progress_cb, "download")
        if not ok:
            tmp_zip.unlink(missing_ok=True)
            return UpdateResult(False, pkg_def.name, current_sha, new_sha,
                                error="Download fehlgeschlagen")

        # Backup wichtiger Konfigurationsdateien
        if progress_cb:
            progress_cb("backup", 91, "Sichere Konfigurationsdateien...")

        preserved = self._backup_configs(install_path)

        # Entpacken (ueberschreiben)
        if progress_cb:
            progress_cb("entpacken", 92, "Entpacke Update...")

        try:
            with zipfile.ZipFile(tmp_zip, "r") as z:
                members = z.namelist()
                prefix = members[0].split("/")[0] + "/" if members else ""
                for member in members:
                    if not member.startswith(prefix):
                        continue
                    rel = member[len(prefix):]
                    if not rel:
                        continue
                    target = install_path / rel
                    if member.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        except Exception as e:
            tmp_zip.unlink(missing_ok=True)
            self._restore_configs(install_path, preserved)
            return UpdateResult(False, pkg_def.name, current_sha, new_sha,
                                error=f"Entpacken fehlgeschlagen: {e}")
        finally:
            tmp_zip.unlink(missing_ok=True)

        # Konfigurationen wiederherstellen
        self._restore_configs(install_path, preserved)

        # Venv-Requirements updaten
        venv_path = install_path / ".venv"
        pip = venv_path / "Scripts" / "pip.exe"
        if not pip.exists():
            pip = venv_path / "bin" / "pip"

        req_file = install_path / pkg_def.pip_requirements
        if req_file.exists() and pip.exists():
            if progress_cb:
                progress_cb("requirements", 96, "Aktualisiere Abhaengigkeiten...")
            try:
                subprocess.run(
                    [str(pip), "install", "-r", str(req_file), "--quiet", "--upgrade"],
                    check=True, capture_output=True, text=True, timeout=600
                )
            except Exception:
                pass  # Nicht kritisch fuer das Update

        if progress_cb:
            progress_cb("fertig", 100, f"Update auf {new_sha} abgeschlossen!")

        return UpdateResult(True, pkg_def.name, current_sha, new_sha)

    def _backup_configs(self, install_path: Path) -> dict[str, bytes]:
        """Sichert bekannte Konfigurationsdateien."""
        config_patterns = [
            "config.json", "ui-config.json", "styles.csv",
            "webui-user.bat", "webui-user.sh",
            "extra-networks.json", "params.txt",
        ]
        backups = {}
        for pattern in config_patterns:
            p = install_path / pattern
            if p.exists() and p.is_file():
                try:
                    backups[pattern] = p.read_bytes()
                except OSError:
                    pass
        return backups

    def _restore_configs(self, install_path: Path, backups: dict[str, bytes]) -> None:
        """Stellt gesicherte Konfigurationsdateien wieder her."""
        for rel_path, content in backups.items():
            target = install_path / rel_path
            try:
                target.write_bytes(content)
            except OSError:
                pass


class SharedFolderManager:
    """Verwaltet Symlinks / Junctions zwischen Master-Ordner und Paketen."""

    def __init__(self, sm_root: Path, master_root: Path):
        self.sm_root = sm_root
        self.master_root = master_root

    def apply_links(self, pkg_def: PackageDef, install_path: Path,
                    progress_cb: ProgressCallback = None) -> list[str]:
        """Erstellt alle Symlinks/Junctions fuer ein Paket. Gibt Fehler-Liste zurueck."""
        errors = []
        total = len(pkg_def.shared_folders)

        for i, rule in enumerate(pkg_def.shared_folders):
            source_info = None
            # Suche Typ in SHARED_FOLDER_TYPES
            from packages_catalog import SHARED_FOLDER_TYPES
            source_info = SHARED_FOLDER_TYPES.get(rule.source_type)
            if not source_info:
                continue

            master_folder = self.master_root / source_info["folder"]
            target_link = install_path / rule.target

            if progress_cb:
                pct = (i / total) * 100
                progress_cb("links", pct, f"{rule.source_type} → {rule.target}")

            # Master-Ordner anlegen falls noetig
            master_folder.mkdir(parents=True, exist_ok=True)

            # Falls Ziel schon ein Link ist, ueberspringen
            if self._is_link(target_link):
                continue

            # Falls Ziel ein echter Ordner mit Inhalt ist, nicht ersetzen
            if target_link.exists() and any(target_link.iterdir()):
                errors.append(f"{rule.target}: Ordner hat Inhalt, wird nicht verlinkt")
                continue

            # Leeren Ordner entfernen oder neu anlegen
            if target_link.exists():
                try:
                    target_link.rmdir()
                except OSError:
                    pass

            # Uebergeordneten Ordner erstellen
            target_link.parent.mkdir(parents=True, exist_ok=True)

            # Junction / Symlink erstellen
            err = self._create_link(master_folder, target_link)
            if err:
                errors.append(f"{rule.target}: {err}")

        if progress_cb:
            progress_cb("links", 100, "Verlinkung abgeschlossen")

        return errors

    def remove_links(self, pkg_def: PackageDef, install_path: Path) -> None:
        """Entfernt alle Symlinks/Junctions eines Pakets."""
        for rule in pkg_def.shared_folders:
            target_link = install_path / rule.target
            if self._is_link(target_link):
                self._remove_link(target_link)

    def _is_link(self, path: Path) -> bool:
        if path.is_symlink():
            return True
        if sys.platform == "win32" and path.exists():
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
            except Exception:
                pass
        return False

    def _create_link(self, source: Path, link: Path) -> str:
        """Erstellt Junction (Win) oder Symlink (Unix). Gibt Fehler oder '' zurueck."""
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(source)],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    return result.stderr.strip() or result.stdout.strip()
            else:
                link.symlink_to(source)
        except Exception as e:
            return str(e)
        return ""

    def _remove_link(self, link: Path) -> None:
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["cmd", "/c", "rmdir", str(link)],
                    capture_output=True
                )
            else:
                link.unlink()
        except Exception:
            pass
