"""
Model Downloader — CivitAI + HuggingFace Download Client
"""

import json
import os
import re
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlparse, unquote

# Shared utilities — Vermeide Duplikation
try:
    from pymatrix.utils import fmt_size as _fmt_size, fmt_speed as _fmt_speed, TIMEOUT_MEDIUM, CHUNK_SIZE_LARGE
except ImportError:
    _fmt_size = _fmt_speed = None
    TIMEOUT_MEDIUM = 120
    CHUNK_SIZE_LARGE = 262144

# ── CivitAI Typ → Master-Typ Mapping ──────────────────────────
CIVITAI_TYPE_MAP = {
    "Checkpoint":        "StableDiffusion",
    "CheckpointMerge":   "StableDiffusion",
    "TextualInversion":  "Embeddings",
    "LORA":              "Lora",
    "LoCon":             "LyCORIS",
    "DoRA":              "Lora",
    "Hypernetwork":      "Hypernetwork",
    "AestheticGradient": "Embeddings",
    "Controlnet":        "ControlNet",
    "VAE":               "VAE",
    "Upscaler":          "ESRGAN",
    "MotionModule":      "SVD",
    "Poses":             "ControlNet",
    "Wildcards":         "Embeddings",
    "Other":             "StableDiffusion",
}

HF_TYPE_GUESS = {
    "checkpoint": "StableDiffusion",
    "lora":       "Lora",
    "vae":        "VAE",
    "controlnet": "ControlNet",
    "embedding":  "Embeddings",
    "text_encoder":"TextEncoders",
    "unet":       "DiffusionModels",
    "upscaler":   "ESRGAN",
}


@dataclass
class ModelInfo:
    """Metadaten zu einem Modell von CivitAI / HuggingFace."""
    source: str       # "civitai" | "huggingface"
    model_id: str
    name: str
    model_type: str   # CivitAI-Typ oder geraten
    master_type: str  # Mapped zu SharedFolderType key
    base_model: str   # z.B. "SDXL 1.0", "SD 1.5", "Flux.1 D"
    description: str
    versions: list    # [{id, name, files: [{name, url, size, type}]}]
    thumbnail: str


@dataclass
class DownloadTask:
    """Ein einzelner Download-Auftrag."""
    url: str
    dest_path: Path
    filename: str
    model_name: str
    file_size: int = 0
    downloaded: int = 0
    speed: float = 0.0
    status: str = "queued"     # queued | downloading | complete | error | cancelled
    error_msg: str = ""
    progress: float = 0.0     # 0.0 .. 1.0
    _cancel: bool = False

    def cancel(self):
        self._cancel = True
        self.status = "cancelled"


class CivitAIClient:
    """CivitAI API v1 Client."""
    API_BASE = "https://civitai.com/api/v1"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def _headers(self) -> dict:
        h = {"User-Agent": "SD-Model-Manager/2.0"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _get_json(self, url: str) -> dict:
        req = Request(url, headers=self._headers())
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def parse_url(self, url: str) -> Optional[str]:
        """Extrahiert Model-ID aus CivitAI URL."""
        m = re.search(r"civitai\.com/models/(\d+)", url)
        return m.group(1) if m else None

    def fetch_model(self, model_id: str) -> ModelInfo:
        """Ruft Modell-Metadaten von CivitAI API ab."""
        data = self._get_json(f"{self.API_BASE}/models/{model_id}")

        model_type = data.get("type", "Checkpoint")
        master_type = CIVITAI_TYPE_MAP.get(model_type, "StableDiffusion")

        versions = []
        for v in data.get("modelVersions", [])[:10]:
            files = []
            for f in v.get("files", []):
                dl_url = f.get("downloadUrl", "")
                if self.api_key and dl_url:
                    dl_url += f"{'&' if '?' in dl_url else '?'}token={self.api_key}"
                files.append({
                    "name": f.get("name", "unknown"),
                    "url": dl_url,
                    "size": f.get("sizeKB", 0) * 1024,
                    "type": f.get("type", "Model"),
                    "format": f.get("metadata", {}).get("format", ""),
                    "fp": f.get("metadata", {}).get("fp", ""),
                })
            versions.append({
                "id": v.get("id"),
                "name": v.get("name", ""),
                "base_model": v.get("baseModel", ""),
                "files": files,
            })

        base_model = versions[0]["base_model"] if versions else ""
        images = data.get("modelVersions", [{}])[0].get("images", [])
        thumbnail = images[0].get("url", "") if images else ""

        return ModelInfo(
            source="civitai",
            model_id=str(model_id),
            name=data.get("name", "Unbekannt"),
            model_type=model_type,
            master_type=master_type,
            base_model=base_model,
            description=data.get("description", "")[:300],
            versions=versions,
            thumbnail=thumbnail,
        )

    def search(self, query: str, model_type: str = "", limit: int = 20) -> list[dict]:
        """Sucht Modelle auf CivitAI."""
        params = f"limit={limit}&query={query}&sort=Highest%20Rated"
        if model_type:
            params += f"&types={model_type}"
        data = self._get_json(f"{self.API_BASE}/models?{params}")
        results = []
        for item in data.get("items", []):
            versions = item.get("modelVersions", [])
            base = versions[0].get("baseModel", "") if versions else ""
            results.append({
                "id": item["id"],
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "base_model": base,
                "stats": item.get("stats", {}),
            })
        return results


class HuggingFaceClient:
    """HuggingFace Hub einfacher Client."""
    API_BASE = "https://huggingface.co/api"

    def parse_url(self, url: str) -> Optional[str]:
        """Extrahiert repo_id aus HuggingFace URL."""
        m = re.search(r"huggingface\.co/([^/]+/[^/\s?#]+)", url)
        return m.group(1) if m else None

    def _get_json(self, url: str) -> dict:
        req = Request(url, headers={"User-Agent": "SD-Model-Manager/2.0"})
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def fetch_model(self, repo_id: str) -> ModelInfo:
        """Ruft Modell-Metadaten von HuggingFace ab."""
        data = self._get_json(f"{self.API_BASE}/models/{repo_id}")

        # Typ erraten aus Tags
        tags = data.get("tags", [])
        model_type = "Checkpoint"
        master_type = "StableDiffusion"
        for tag in tags:
            tag_lower = tag.lower()
            for key, mt in HF_TYPE_GUESS.items():
                if key in tag_lower:
                    model_type = key.title()
                    master_type = mt
                    break

        # Dateien auflisten
        siblings = data.get("siblings", [])
        files = []
        for s in siblings:
            fname = s.get("rfilename", "")
            if any(fname.endswith(ext) for ext in
                   [".safetensors", ".ckpt", ".pt", ".bin", ".pth", ".gguf"]):
                files.append({
                    "name": fname,
                    "url": f"https://huggingface.co/{repo_id}/resolve/main/{fname}",
                    "size": 0,
                    "type": "Model",
                })

        versions = [{
            "id": repo_id,
            "name": "main",
            "base_model": "",
            "files": files,
        }]

        return ModelInfo(
            source="huggingface",
            model_id=repo_id,
            name=data.get("modelId", repo_id).split("/")[-1],
            model_type=model_type,
            master_type=master_type,
            base_model="",
            description="",
            versions=versions,
            thumbnail="",
        )


class DownloadManager:
    """Verwaltet Download-Warteschlange und parallele Downloads."""

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.tasks: list[DownloadTask] = []
        self._lock = threading.Lock()
        self._running = 0
        self.on_progress: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None

    def add_download(self, url: str, dest_dir: Path, filename: str,
                     model_name: str = "", file_size: int = 0) -> DownloadTask:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        task = DownloadTask(
            url=url,
            dest_path=dest_path,
            filename=filename,
            model_name=model_name or filename,
            file_size=file_size,
        )
        with self._lock:
            self.tasks.append(task)
        self._check_queue()
        return task

    def _check_queue(self):
        with self._lock:
            if self._running >= self.max_concurrent:
                return
            for task in self.tasks:
                if task.status == "queued":
                    task.status = "downloading"
                    self._running += 1
                    t = threading.Thread(target=self._download_worker,
                                         args=(task,), daemon=True)
                    t.start()
                    if self._running >= self.max_concurrent:
                        break

    def _download_worker(self, task: DownloadTask):
        try:
            req = Request(task.url, headers={
                "User-Agent": "SD-Model-Manager/2.0",
            })

            # Resume support
            existing_size = 0
            tmp_path = task.dest_path.with_suffix(task.dest_path.suffix + ".part")
            if tmp_path.exists():
                existing_size = tmp_path.stat().st_size
                req.add_header("Range", f"bytes={existing_size}-")

            with urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                if resp.status == 206:  # Partial content
                    total += existing_size
                elif existing_size > 0:
                    existing_size = 0  # Server doesn't support range

                if total > 0:
                    task.file_size = total
                task.downloaded = existing_size

                mode = "ab" if existing_size > 0 else "wb"
                chunk_size = 1024 * 256  # 256 KB
                last_time = time.time()
                last_bytes = existing_size

                with open(tmp_path, mode) as f:
                    while True:
                        if task._cancel:
                            break
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        task.downloaded += len(chunk)

                        # Progress & Speed
                        now = time.time()
                        dt = now - last_time
                        if dt >= 0.5:
                            task.speed = (task.downloaded - last_bytes) / dt
                            last_time = now
                            last_bytes = task.downloaded

                        if task.file_size > 0:
                            task.progress = task.downloaded / task.file_size

                        if self.on_progress:
                            self.on_progress(task)

            if task._cancel:
                task.status = "cancelled"
            else:
                # Rename .part → final
                if task.dest_path.exists():
                    task.dest_path.unlink()
                tmp_path.rename(task.dest_path)
                task.status = "complete"
                task.progress = 1.0

        except Exception as e:
            task.status = "error"
            task.error_msg = str(e)

        with self._lock:
            self._running -= 1

        if self.on_complete:
            self.on_complete(task)
        self._check_queue()

    def cancel_all(self):
        for task in self.tasks:
            if task.status in ("queued", "downloading"):
                task.cancel()

    def clear_completed(self):
        with self._lock:
            self.tasks = [t for t in self.tasks
                          if t.status not in ("complete", "cancelled", "error")]


def fmt_size(bytes_val: int | float) -> str:
    """Formatiert Bytes als menschenlesbare Groesse. (Delegiert an pymatrix.utils)"""
    if _fmt_size:
        return _fmt_size(bytes_val)
    if bytes_val <= 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def fmt_speed(bytes_per_sec: float) -> str:
    """Formatiert Download-Geschwindigkeit. (Delegiert an pymatrix.utils)"""
    if _fmt_speed:
        return _fmt_speed(bytes_per_sec)
    return f"{fmt_size(bytes_per_sec)}/s"


def detect_source(url: str) -> str:
    """Erkennt ob URL CivitAI oder HuggingFace ist."""
    if "civitai.com" in url:
        return "civitai"
    elif "huggingface.co" in url:
        return "huggingface"
    return "unknown"
