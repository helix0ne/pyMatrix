"""
Model Scanner — Disk-Analyse, Duplikat-Erkennung, Orphan-Finder
"""

import hashlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Shared utilities
try:
    from pymatrix.utils import fmt_size as _shared_fmt_size
except ImportError:
    _shared_fmt_size = None


MODEL_EXTENSIONS = {
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin",
    ".onnx", ".gguf", ".pkl",
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".preview.png",
}


@dataclass
class FileInfo:
    path: Path
    size: int
    name: str
    extension: str
    is_model: bool


@dataclass
class FolderStats:
    key: str
    label: str
    path: Path
    exists: bool
    file_count: int = 0
    model_count: int = 0
    total_bytes: int = 0
    largest_file: str = ""
    largest_size: int = 0
    is_symlink: bool = False


@dataclass
class DuplicateGroup:
    hash_val: str
    size: int
    files: list[Path] = field(default_factory=list)


@dataclass
class OrphanFile:
    path: Path
    size: int
    webui_name: str
    suggested_type: str


def scan_folder_sizes(master_root: str, master_types: dict,
                      progress_cb: Optional[Callable] = None) -> list[FolderStats]:
    """Scannt alle Master-Typ-Ordner und gibt Statistiken zurueck."""
    root = Path(master_root)
    results = []
    total = len(master_types)

    for i, (key, mt) in enumerate(sorted(master_types.items())):
        folder = root / mt.get("folder", key)
        stats = FolderStats(
            key=key,
            label=mt.get("label", key),
            path=folder,
            exists=folder.exists(),
        )

        if folder.exists():
            stats.is_symlink = folder.is_symlink()
            try:
                for f in folder.rglob("*"):
                    if f.is_file():
                        try:
                            size = f.stat().st_size
                        except OSError:
                            continue
                        stats.file_count += 1
                        stats.total_bytes += size
                        ext = f.suffix.lower()
                        if ext in MODEL_EXTENSIONS:
                            stats.model_count += 1
                        if size > stats.largest_size:
                            stats.largest_size = size
                            stats.largest_file = f.name
            except PermissionError:
                pass

        results.append(stats)
        if progress_cb:
            progress_cb(i + 1, total, key)

    return results


def _quick_hash(filepath: Path, chunk_size: int = 65536) -> str:
    """Schneller Hash: Erste + Letzte 64KB + Dateigroesse."""
    size = filepath.stat().st_size
    h = hashlib.sha256()
    h.update(str(size).encode())

    with open(filepath, "rb") as f:
        h.update(f.read(chunk_size))
        if size > chunk_size * 2:
            f.seek(-chunk_size, 2)
            h.update(f.read(chunk_size))

    return h.hexdigest()[:16]


def find_duplicates(master_root: str,
                    progress_cb: Optional[Callable] = None) -> list[DuplicateGroup]:
    """Findet doppelte Modelldateien im Master-Root."""
    root = Path(master_root)
    if not root.exists():
        return []

    # Phase 1: Alle Modelldateien sammeln
    all_files: list[tuple[Path, int]] = []
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in MODEL_EXTENSIONS:
            try:
                all_files.append((f, f.stat().st_size))
            except OSError:
                continue

    if progress_cb:
        progress_cb(0, len(all_files), "Dateien gesammelt")

    # Phase 2: Nach Groesse gruppieren (schneller Vorfilter)
    size_groups: dict[int, list[Path]] = {}
    for path, size in all_files:
        if size > 1024:  # Ignoriere winzige Dateien
            size_groups.setdefault(size, []).append(path)

    # Nur Gruppen mit >1 Datei gleicher Groesse
    candidates = {s: paths for s, paths in size_groups.items() if len(paths) > 1}

    # Phase 3: Hash-basierte Pruefung
    duplicates: list[DuplicateGroup] = []
    done = 0
    total = sum(len(paths) for paths in candidates.values())

    for size, paths in candidates.items():
        hash_groups: dict[str, list[Path]] = {}
        for p in paths:
            try:
                h = _quick_hash(p)
                hash_groups.setdefault(h, []).append(p)
            except (OSError, PermissionError):
                continue
            done += 1
            if progress_cb:
                progress_cb(done, total, p.name)

        for h, group in hash_groups.items():
            if len(group) > 1:
                duplicates.append(DuplicateGroup(
                    hash_val=h,
                    size=size,
                    files=sorted(group),
                ))

    return sorted(duplicates, key=lambda d: -d.size)


def find_orphans(packages_root: str, profiles: dict,
                 progress_cb: Optional[Callable] = None) -> list[OrphanFile]:
    """Findet echte Modelldateien in WebUI-Paketen (nicht-Symlinks)."""
    root = Path(packages_root)
    if not root.exists():
        return []

    orphans = []
    profile_list = list(profiles.values())
    total = len(profile_list)

    for i, prof in enumerate(profile_list):
        pkg_dir = root / prof.get("package_folder", "")
        if not pkg_dir.exists():
            continue

        webui_name = prof.get("display_name", prof.get("name", "?"))

        for rule in prof.get("rules", []):
            target_path = pkg_dir / rule.get("target", "")
            if not target_path.exists():
                continue

            # Ist der Zielordner ein Symlink/Junction?
            # Wenn ja, ist er korrekt verknuepft → kein Orphan
            try:
                if target_path.is_symlink():
                    continue
                if sys.platform == "win32" and target_path.exists():
                    if bool(target_path.stat().st_file_attributes & 0x400):
                        continue  # Reparse Point / Junction
            except (OSError, AttributeError):
                continue  # Zugriffsfehler → ueberspringe

            # Echte Dateien suchen
            try:
                for f in target_path.rglob("*"):
                    if f.is_file() and f.suffix.lower() in MODEL_EXTENSIONS:
                        try:
                            size = f.stat().st_size
                        except OSError:
                            continue
                        if size > 1024:  # Ignoriere Placeholder
                            types = rule.get("source_types", [])
                            suggested = types[0] if types else "StableDiffusion"
                            orphans.append(OrphanFile(
                                path=f,
                                size=size,
                                webui_name=webui_name,
                                suggested_type=suggested,
                            ))
            except PermissionError:
                pass

        if progress_cb:
            progress_cb(i + 1, total, webui_name)

    return sorted(orphans, key=lambda o: -o.size)


def fmt_size(bytes_val: int | float) -> str:
    """Formatiert Bytes als menschenlesbare Groesse. (Delegiert an pymatrix.utils)"""
    if _shared_fmt_size:
        return _shared_fmt_size(bytes_val)
    if bytes_val <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"
