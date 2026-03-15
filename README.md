<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/version-2.0.0-00ff88?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/platform-windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" />
</p>

<h1 align="center">
  <br>
  pyMatrix
  <br>
  <sub>AI Package Manager &middot; Model Manager &middot; Multi-WebUI Symlink Engine</sub>
</h1>

<p align="center">
  A <strong>StabilityMatrix-compatible</strong> Python toolkit for managing AI image generation packages,<br>
  models, and symlinks across <strong>12 WebUI runtimes</strong> — with 5 themed web dashboards.
</p>

---

## What is pyMatrix?

pyMatrix is an open-source tool that sits on top of [StabilityMatrix](https://github.com/LykosAI/StabilityMatrix) and provides:

- **Package Management** — Launch, stop, configure and monitor 19 AI packages (A1111, ComfyUI, Forge, Fooocus, InvokeAI, Kohya SS, …)
- **Universal Model Manager** — One shared model library with automatic symlinks to every WebUI's folder structure
- **Model Scanner** — Detect orphaned files, duplicates, and wasted disk space across all packages
- **5 Web Dashboards** — Each with a unique design language, served via built-in HTTP server
- **AI Universe Map** — Interactive force-directed graph mapping the entire Stable Diffusion ecosystem

---

## Supported WebUI Profiles

| Profile | Repository | Symlink Rules |
|---------|-----------|---------------|
| **A1111** | AUTOMATIC1111/stable-diffusion-webui | 15 folder types |
| **Forge** | lllyasviel/stable-diffusion-webui-forge | 15 folder types |
| **Forge Neo** | Haoming02/sd-webui-forge-classic | 15 folder types |
| **reForge** | Panchovix/stable-diffusion-webui-reforge | 15 folder types |
| **ComfyUI** | comfyanonymous/ComfyUI | 12 folder types |
| **SD.Next** | vladmandic/automatic | 14 folder types |
| **InvokeAI** | invoke-ai/InvokeAI | 8 folder types |
| **Fooocus** | lllyasviel/Fooocus | 6 folder types |
| **Fooocus MRE** | MoonRide303/Fooocus-MRE | 6 folder types |
| **Kohya SS** | bmaltais/kohya_ss | 4 folder types |
| **SwarmUI** | mcmonkeyprojects/SwarmUI | 10 folder types |
| **FluxGym** | cocktailpeanut/fluxgym | 3 folder types |

---

## 32 Shared Folder Types

pyMatrix maps **32 model categories** from the StabilityMatrix `SharedFolderType` enum into a single master library:

```
models/
├── Checkpoints/        # Full models (.safetensors, .ckpt)
├── Lora/               # LoRA adapters
├── LyCORIS/            # LoHA, LoKr, DyLoRA
├── VAE/                # Variational Autoencoders
├── ControlNet/         # ControlNet models
├── Embeddings/         # Textual Inversion
├── CLIP/               # CLIP models
├── Diffusers/          # HuggingFace Diffusers format
├── ESRGAN/             # Upscaler models
├── IPAdapter/          # IP-Adapter
├── T2IAdapter/         # T2I Adapter
├── Hypernetwork/       # Hypernetworks
├── ...                 # + 20 more types
```

Each WebUI profile defines rules mapping these master types to its own expected folder paths. pyMatrix creates **symlinks** so every runtime sees the same files — zero duplication.

---

## Dashboards

Five themed HTML dashboards, each fully standalone (no build tools, no npm):

| # | Theme | File | Design Language |
|---|-------|------|-----------------|
| 1 | **Cyberpunk** | `dashboard/index.html` | Neon cyan/magenta, dark terminal aesthetic |
| 2 | **Gradio Light** | `dashboard/gradio.html` | Clean white UI inspired by Gradio |
| 3 | **Mission Control** | `dashboard/control.html` | Amber CRT / NASA telemetry |
| 4 | **Ultimate Manager** | `dashboard/manager.html` | Neo-brutalist dark, IBM Plex |
| 5 | **Editorial** | `dashboard/models.html` | Rust/paper minimal, Playfair Display |

All dashboards include:
- Package launcher with status indicators
- Model folder overview with size breakdowns
- Symlink matrix (type × profile coverage)
- Model scanner & duplicate finder
- Cross-navigation via floating `🔀` switcher button

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Windows** (symlinks require admin rights or Developer Mode)
- [StabilityMatrix](https://github.com/LykosAI/StabilityMatrix) installed (optional but recommended)

### Installation

```bash
git clone https://github.com/helix0ne/pyMatrix.git
cd pyMatrix
pip install -r requirements.txt
```

### Launch Dashboard

```bash
python -m http.server 5173 -d pymatrix/dashboard
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

### Launch Desktop GUI

```bash
python -m pymatrix.app
```

### Launch Model Manager GUI

```bash
python -m pymatrix.model_manager_app
```

### Symlink Dry Run (Preview Only)

```powershell
# See what would be linked — no changes made
python -m pymatrix.model_manager --dry-run
```

### Apply Symlinks

```powershell
# Run as Administrator
python -m pymatrix.model_manager --apply
```

---

## Project Structure

```
pyMatrix/
├── pymatrix/
│   ├── __init__.py              # Package metadata (v2.0.0)
│   ├── app.py                   # Desktop GUI (customtkinter)
│   ├── core.py                  # SM config, package launcher, model library
│   ├── packages_catalog.py      # 19 package definitions with launch options
│   ├── installer.py             # GitHub archive downloader, venv builder
│   ├── extensions.py            # Custom Nodes & Extensions manager
│   ├── model_manager.py         # Symlink engine — multi-WebUI linker
│   ├── model_manager_app.py     # Model Manager GUI (customtkinter)
│   ├── scanner.py               # Model scanner & duplicate finder
│   ├── downloader.py            # CivitAI / HuggingFace model downloader
│   ├── generate_map.py          # AI Universe Map generator
│   ├── config/
│   │   └── master_types.json    # 32 SharedFolderType definitions
│   ├── profiles/                # WebUI symlink profiles
│   │   ├── A1111.json
│   │   ├── ComfyUI.json
│   │   ├── Forge.json
│   │   └── ... (11 profiles)
│   └── dashboard/               # 5 themed HTML dashboards
│       ├── index.html           # Cyberpunk
│       ├── gradio.html          # Gradio Light
│       ├── control.html         # Mission Control
│       ├── manager.html         # Ultimate Manager
│       └── models.html          # Editorial
├── setup_model_symlinks.ps1     # PowerShell symlink script (standalone)
├── SD_UNIVERSAL_MODEL_STRUCTURE.md
├── requirements.txt
└── .gitignore
```

---

## How Symlinks Work

```
Master Library                    WebUI Package Folder
─────────────────                 ──────────────────────────
models/Checkpoints/    ◄─────►   Packages/Forge/models/Stable-diffusion/
models/Lora/           ◄─────►   Packages/Forge/models/Lora/
models/VAE/            ◄─────►   Packages/Forge/models/VAE/
models/ControlNet/     ◄─────►   Packages/ComfyUI/models/controlnet/
models/Lora/           ◄─────►   Packages/ComfyUI/models/loras/
models/Checkpoints/    ◄─────►   Packages/ComfyUI/models/checkpoints/
```

One download, every WebUI sees it. No disk space wasted.

---

## Configuration

### Master Types (`config/master_types.json`)

Defines the canonical folder structure. Extracted from StabilityMatrix's C# `SharedFolderType` enum.

### WebUI Profiles (`profiles/*.json`)

Each JSON file maps master types to the WebUI's expected paths:

```json
{
  "name": "Forge",
  "package": "stable-diffusion-webui-forge",
  "rules": [
    { "source_type": "StableDiffusion", "target": "models/Stable-diffusion" },
    { "source_type": "Lora",            "target": "models/Lora" },
    { "source_type": "VAE",             "target": "models/VAE" },
    { "source_type": "ControlNet",      "target": "models/ControlNet" }
  ]
}
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop GUI | [customtkinter](https://github.com/TomSchimansky/CustomTkinter) |
| Web Dashboards | Vanilla HTML/CSS/JS (zero dependencies) |
| Backend | Python 3.10+ stdlib |
| HTTP Server | `python -m http.server` |
| Downloads | `requests` + `urllib` fallback |
| Symlinks | `os.symlink()` / `mklink` |
| Fonts | Inter, Fira Code, JetBrains Mono, Chakra Petch, IBM Plex, Playfair Display (Google Fonts CDN) |

---

## Roadmap

- [ ] Live backend API connecting dashboards to Python core
- [ ] CivitAI / HuggingFace one-click model downloads from dashboard
- [ ] AI Universe Map expansion (2000+ nodes, searchable)
- [ ] Linux / macOS symlink support
- [ ] Ollama / LLM package integration
- [ ] Auto-update via GitHub releases

---

## Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/awesome`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with Python &middot; Powered by StabilityMatrix
  <br>
  <sub>Made by <a href="https://github.com/helix0ne">helix0ne</a></sub>
</p>
