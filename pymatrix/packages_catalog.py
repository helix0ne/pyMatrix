"""
PyMatrix Package Catalog — Vollstaendige Paket-Metadaten
Extrahiert aus StabilityMatrix C# Quellcode, erweitert fuer PyMatrix.
19 unterstuetzte WebUI / Training Pakete.
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Shared Folder Types (aus SM SharedFolderType Enum) ─────────────
SHARED_FOLDER_TYPES = {
    "StableDiffusion":      {"label": "Checkpoints",      "folder": "StableDiffusion"},
    "LORA":                 {"label": "LoRA",              "folder": "Lora"},
    "LyCORIS":              {"label": "LyCORIS",           "folder": "LyCORIS"},
    "InvokeAIModels":       {"label": "InvokeAI Models",   "folder": "InvokeAI/autoimport"},
    "VAE":                  {"label": "VAE",               "folder": "VAE"},
    "Hypernetwork":         {"label": "Hypernetworks",     "folder": "Hypernetwork"},
    "TextualInversion":     {"label": "Embeddings",        "folder": "TextualInversion"},
    "ControlNet":           {"label": "ControlNet",        "folder": "ControlNet"},
    "GFPGAN":               {"label": "GFPGAN",            "folder": "GFPGAN"},
    "ESRGAN":               {"label": "ESRGAN / Upscalers","folder": "ESRGAN"},
    "RealESRGAN":           {"label": "Real-ESRGAN",       "folder": "RealESRGAN"},
    "SwinIR":               {"label": "SwinIR",            "folder": "SwinIR"},
    "Deepbooru":            {"label": "Deepbooru",         "folder": "Deepbooru"},
    "Codeformer":           {"label": "Codeformer",        "folder": "Codeformer"},
    "LDSR":                 {"label": "LDSR",              "folder": "LDSR"},
    "AfterDetailer":        {"label": "ADetailer",         "folder": "adetailer"},
    "Diffusers":            {"label": "Diffusers",         "folder": "Diffusers"},
    "CLIP":                 {"label": "CLIP",              "folder": "CLIP"},
    "InvokeAINodes":        {"label": "InvokeAI Nodes",    "folder": "InvokeAI/nodes"},
    "T2IAdapter":           {"label": "T2I Adapter",       "folder": "T2IAdapter"},
    "IPAdapter":            {"label": "IP-Adapter",        "folder": "IpAdapter"},
    "PromptExpansion":      {"label": "Prompt Expansion",  "folder": "PromptExpansion"},
    "Upscalers":            {"label": "Upscalers",         "folder": "Upscalers"},
    "Lora":                 {"label": "LoRA (alt)",        "folder": "Lora"},
}


@dataclass
class LaunchOption:
    name: str           # --flag oder leer fuer positional
    arg_type: str       # "Bool" | "String" | "OptionString"
    default: object     # bool oder str
    description: str = ""


@dataclass
class SharedFolderRule:
    source_type: str    # Key aus SHARED_FOLDER_TYPES
    target: str         # Relativer Pfad im Paket-Ordner


@dataclass
class PackageDef:
    name: str               # Interner Schluessel (wie SM PackageName)
    display_name: str       # Anzeigename
    author: str
    github_repo: str        # "user/repo"
    branch: str             # default branch
    description: str
    launch_script: str      # z.B. "launch.py" oder "main.py"
    color: str              # Catppuccin-Farbe
    icon: str               # Unicode-Symbol
    tags: list[str] = field(default_factory=list)
    shared_folders: list[SharedFolderRule] = field(default_factory=list)
    launch_options: list[LaunchOption] = field(default_factory=list)
    pip_requirements: str = "requirements.txt"
    min_python: str = "3.10"
    homepage: str = ""
    preview_image: str = ""   # URL zu Vorschaubild
    is_training: bool = False  # Training-Tool (nicht WebUI)


# ── PACKAGE CATALOG ──────────────────────────────────────────────────

PACKAGE_CATALOG: dict[str, PackageDef] = {

    "stable-diffusion-webui": PackageDef(
        name="stable-diffusion-webui",
        display_name="AUTOMATIC1111 WebUI",
        author="AUTOMATIC1111",
        github_repo="AUTOMATIC1111/stable-diffusion-webui",
        branch="master",
        description="Der klassische Stable Diffusion WebUI mit umfangreichem Extension-System.",
        launch_script="launch.py",
        color="#89b4fa",
        icon="■",
        tags=["webui", "classic", "extensions"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/Stable-diffusion"),
            SharedFolderRule("VAE",             "models/VAE"),
            SharedFolderRule("LORA",            "models/Lora"),
            SharedFolderRule("LyCORIS",         "models/LyCORIS"),
            SharedFolderRule("TextualInversion","embeddings"),
            SharedFolderRule("Hypernetwork",    "models/hypernetworks"),
            SharedFolderRule("ControlNet",      "models/ControlNet"),
            SharedFolderRule("ESRGAN",          "models/ESRGAN"),
            SharedFolderRule("RealESRGAN",      "models/RealESRGAN"),
            SharedFolderRule("SwinIR",          "models/SwinIR"),
            SharedFolderRule("Deepbooru",       "models/torch_deepdanbooru"),
            SharedFolderRule("Codeformer",      "models/Codeformer"),
            SharedFolderRule("LDSR",            "models/LDSR"),
            SharedFolderRule("AfterDetailer",   "models/adetailer"),
        ],
        launch_options=[
            LaunchOption("--api",             "Bool",   False, "REST API aktivieren"),
            LaunchOption("--xformers",        "Bool",   False, "xFormers Memory-Optimierung"),
            LaunchOption("--medvram",         "Bool",   False, "Medium VRAM Modus"),
            LaunchOption("--lowvram",         "Bool",   False, "Low VRAM Modus"),
            LaunchOption("--no-half",         "Bool",   False, "Float32 statt Float16"),
            LaunchOption("--port",            "String", "7860","Listening Port"),
            LaunchOption("--listen",          "Bool",   False, "Auf allen Interfaces lauschen"),
            LaunchOption("--share",           "Bool",   False, "Gradio Share Link"),
        ],
        homepage="https://github.com/AUTOMATIC1111/stable-diffusion-webui",
    ),

    "stable-diffusion-webui-forge": PackageDef(
        name="stable-diffusion-webui-forge",
        display_name="SD WebUI Forge",
        author="lllyasviel",
        github_repo="lllyasviel/stable-diffusion-webui-forge",
        branch="main",
        description="Forge basiert auf A1111 mit massiven Performance-Verbesserungen fuer GPU-Speicher.",
        launch_script="launch.py",
        color="#fab387",
        icon="▶",
        tags=["webui", "forge", "performance"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/Stable-diffusion"),
            SharedFolderRule("VAE",             "models/VAE"),
            SharedFolderRule("LORA",            "models/Lora"),
            SharedFolderRule("LyCORIS",         "models/LyCORIS"),
            SharedFolderRule("TextualInversion","embeddings"),
            SharedFolderRule("Hypernetwork",    "models/hypernetworks"),
            SharedFolderRule("ControlNet",      "models/ControlNet"),
            SharedFolderRule("ESRGAN",          "models/ESRGAN"),
            SharedFolderRule("AfterDetailer",   "models/adetailer"),
            SharedFolderRule("IPAdapter",       "models/ipadapter"),
        ],
        launch_options=[
            LaunchOption("--api",             "Bool",   False, "REST API aktivieren"),
            LaunchOption("--xformers",        "Bool",   False, "xFormers"),
            LaunchOption("--medvram",         "Bool",   False, "Medium VRAM"),
            LaunchOption("--lowvram",         "Bool",   False, "Low VRAM"),
            LaunchOption("--port",            "String", "7860","Port"),
            LaunchOption("--listen",          "Bool",   False, "Alle Interfaces"),
            LaunchOption("--cuda-malloc",     "Bool",   False, "CUDA Malloc Optimierung"),
            LaunchOption("--cuda-stream",     "Bool",   False, "CUDA Stream"),
        ],
        homepage="https://github.com/lllyasviel/stable-diffusion-webui-forge",
    ),

    "forge-neo": PackageDef(
        name="forge-neo",
        display_name="Forge Neo",
        author="Haoming02",
        github_repo="Haoming02/sd-webui-forge-classic",
        branch="neo",
        description="Forge Neo — experimenteller Branch mit neuen Features.",
        launch_script="launch.py",
        color="#f38ba8",
        icon="▶",
        tags=["webui", "forge", "experimental"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/Stable-diffusion"),
            SharedFolderRule("VAE",             "models/VAE"),
            SharedFolderRule("LORA",            "models/Lora"),
            SharedFolderRule("TextualInversion","embeddings"),
            SharedFolderRule("ControlNet",      "models/ControlNet"),
        ],
        launch_options=[
            LaunchOption("--api",   "Bool",   False, "API"),
            LaunchOption("--port",  "String", "7860","Port"),
        ],
        homepage="https://github.com/Haoming02/sd-webui-forge-classic",
    ),

    "reforge": PackageDef(
        name="reforge",
        display_name="SD WebUI reForge",
        author="Panchovix",
        github_repo="Panchovix/stable-diffusion-webui-reForge",
        branch="main",
        description="reForge — A1111-basiert mit Forge-Optimierungen und eigenen Features.",
        launch_script="launch.py",
        color="#cba6f7",
        icon="▶",
        tags=["webui", "forge"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/Stable-diffusion"),
            SharedFolderRule("VAE",             "models/VAE"),
            SharedFolderRule("LORA",            "models/Lora"),
            SharedFolderRule("LyCORIS",         "models/LyCORIS"),
            SharedFolderRule("TextualInversion","embeddings"),
            SharedFolderRule("ControlNet",      "models/ControlNet"),
            SharedFolderRule("ESRGAN",          "models/ESRGAN"),
        ],
        launch_options=[
            LaunchOption("--api",   "Bool",   False, "API"),
            LaunchOption("--port",  "String", "7860","Port"),
            LaunchOption("--listen","Bool",   False, "Alle Interfaces"),
        ],
        homepage="https://github.com/Panchovix/stable-diffusion-webui-reForge",
    ),

    "forge-classic": PackageDef(
        name="forge-classic",
        display_name="ForgeClassic",
        author="Haoming02",
        github_repo="Haoming02/sd-webui-forge-classic",
        branch="classic",
        description="ForgeClassic — Stabiler Forge-Branch, kompatibel mit aelteren Extensions.",
        launch_script="launch.py",
        color="#89dceb",
        icon="▶",
        tags=["webui", "forge", "stable"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/Stable-diffusion"),
            SharedFolderRule("VAE",             "models/VAE"),
            SharedFolderRule("LORA",            "models/Lora"),
            SharedFolderRule("TextualInversion","embeddings"),
            SharedFolderRule("ControlNet",      "models/ControlNet"),
        ],
        launch_options=[
            LaunchOption("--api",   "Bool",   False, "API"),
            LaunchOption("--port",  "String", "7860","Port"),
        ],
        homepage="https://github.com/Haoming02/sd-webui-forge-classic",
    ),

    "ComfyUI": PackageDef(
        name="ComfyUI",
        display_name="ComfyUI",
        author="comfyanonymous",
        github_repo="comfyanonymous/ComfyUI",
        branch="master",
        description="Node-basierter Workflow-Editor fuer Stable Diffusion. Maximale Flexibilitaet.",
        launch_script="main.py",
        color="#a6e3a1",
        icon="◆",
        tags=["webui", "nodes", "workflow"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/checkpoints"),
            SharedFolderRule("VAE",             "models/vae"),
            SharedFolderRule("LORA",            "models/loras"),
            SharedFolderRule("LyCORIS",         "models/loras"),
            SharedFolderRule("TextualInversion","models/embeddings"),
            SharedFolderRule("Hypernetwork",    "models/hypernetworks"),
            SharedFolderRule("ControlNet",      "models/controlnet"),
            SharedFolderRule("ESRGAN",          "models/upscale_models"),
            SharedFolderRule("RealESRGAN",      "models/upscale_models"),
            SharedFolderRule("IPAdapter",       "models/ipadapter"),
            SharedFolderRule("T2IAdapter",      "models/t2i_adapter"),
            SharedFolderRule("CLIP",            "models/clip"),
            SharedFolderRule("Diffusers",       "models/diffusers"),
        ],
        launch_options=[
            LaunchOption("--port",              "String", "8188","Port"),
            LaunchOption("--listen",            "String", "127.0.0.1","Listen-IP"),
            LaunchOption("--cuda-device",       "String", "",   "CUDA Device Index"),
            LaunchOption("--lowvram",           "Bool",   False,"Low VRAM"),
            LaunchOption("--novram",            "Bool",   False,"No VRAM"),
            LaunchOption("--cpu",               "Bool",   False,"CPU Modus"),
            LaunchOption("--fp16-vae",          "Bool",   False,"FP16 VAE"),
            LaunchOption("--bf16-unet",         "Bool",   False,"BF16 UNet"),
            LaunchOption("--disable-xformers",  "Bool",   False,"xFormers deaktivieren"),
            LaunchOption("--fast",              "Bool",   False,"Schnellmodus (experimentell)"),
        ],
        homepage="https://github.com/comfyanonymous/ComfyUI",
    ),

    "automatic": PackageDef(
        name="automatic",
        display_name="SD.Next (vladmandic)",
        author="vladmandic",
        github_repo="vladmandic/automatic",
        branch="master",
        description="SD.Next — moderner A1111-Fork mit Backend-Wechsel (diffusers, original, etc.).",
        launch_script="launch.py",
        color="#f2cdcd",
        icon="▶",
        tags=["webui", "advanced"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/Stable-diffusion"),
            SharedFolderRule("VAE",             "models/VAE"),
            SharedFolderRule("LORA",            "models/Lora"),
            SharedFolderRule("TextualInversion","embeddings"),
            SharedFolderRule("ControlNet",      "models/ControlNet"),
            SharedFolderRule("ESRGAN",          "models/ESRGAN"),
        ],
        launch_options=[
            LaunchOption("--api",       "Bool",   False, "API"),
            LaunchOption("--port",      "String", "7860","Port"),
            LaunchOption("--listen",    "Bool",   False, "Alle Interfaces"),
            LaunchOption("--backend",   "String", "diffusers", "Backend: original/diffusers"),
        ],
        homepage="https://github.com/vladmandic/automatic",
    ),

    "InvokeAI": PackageDef(
        name="InvokeAI",
        display_name="InvokeAI",
        author="invoke-ai",
        github_repo="invoke-ai/InvokeAI",
        branch="main",
        description="InvokeAI — professioneller Workflow-Editor mit eigenem Modell-Management.",
        launch_script="invokeai-web",
        color="#94e2d5",
        icon="◆",
        tags=["webui", "professional"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/core/convert"),
            SharedFolderRule("InvokeAIModels",  "autoimport"),
        ],
        launch_options=[
            LaunchOption("--port",   "String", "9090","Port"),
            LaunchOption("--host",   "String", "127.0.0.1","Host"),
        ],
        homepage="https://github.com/invoke-ai/InvokeAI",
    ),

    "Fooocus": PackageDef(
        name="Fooocus",
        display_name="Fooocus",
        author="lllyasviel",
        github_repo="lllyasviel/Fooocus",
        branch="main",
        description="Fooocus — Einfachstes UI fuer SDXL, inspiriert von Midjourney-Workflow.",
        launch_script="launch.py",
        color="#cba6f7",
        icon="◆",
        tags=["webui", "simple", "sdxl"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/checkpoints"),
            SharedFolderRule("LORA",            "models/loras"),
            SharedFolderRule("VAE",             "models/vae"),
            SharedFolderRule("ControlNet",      "models/controlnet"),
            SharedFolderRule("ESRGAN",          "models/upscale_models"),
        ],
        launch_options=[
            LaunchOption("--listen",    "Bool",   False, "Alle Interfaces"),
            LaunchOption("--port",      "String", "7865","Port"),
            LaunchOption("--share",     "Bool",   False, "Gradio Share"),
        ],
        homepage="https://github.com/lllyasviel/Fooocus",
    ),

    "kohya_ss": PackageDef(
        name="kohya_ss",
        display_name="Kohya GUI",
        author="bmaltais",
        github_repo="bmaltais/kohya_ss",
        branch="master",
        description="Grafische Oberflaeche fuer Kohya LoRA / Dreambooth Training.",
        launch_script="kohya_gui.py",
        color="#94e2d5",
        icon="⚙",
        tags=["training", "lora", "dreambooth"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/stable_diffusion"),
            SharedFolderRule("LORA",            "models/lora"),
            SharedFolderRule("VAE",             "models/vae"),
        ],
        launch_options=[
            LaunchOption("--listen",    "String", "127.0.0.1","Listen-IP"),
            LaunchOption("--server_port","String","7860","Port"),
            LaunchOption("--headless",  "Bool",   False, "Kein Browser oeffnen"),
        ],
        homepage="https://github.com/bmaltais/kohya_ss",
        is_training=True,
    ),

    "OneTrainer": PackageDef(
        name="OneTrainer",
        display_name="OneTrainer",
        author="Nerogar",
        github_repo="Nerogar/OneTrainer",
        branch="master",
        description="Alles-in-einem Training-Tool: LoRA, DreamBooth, FineTuning fuer SD/SDXL/Flux.",
        launch_script="scripts/train_ui.py",
        color="#f9e2af",
        icon="⚙",
        tags=["training", "lora", "flux"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models/stable_diffusion"),
            SharedFolderRule("LORA",            "models/lora"),
        ],
        launch_options=[],
        homepage="https://github.com/Nerogar/OneTrainer",
        is_training=True,
    ),

    "FluxGym": PackageDef(
        name="FluxGym",
        display_name="FluxGym",
        author="cocktailpeanut",
        github_repo="cocktailpeanut/fluxgym",
        branch="main",
        description="Einfaches Training-Tool speziell fuer Flux-Modelle.",
        launch_script="app.py",
        color="#fab387",
        icon="⚙",
        tags=["training", "flux"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "models"),
        ],
        launch_options=[
            LaunchOption("--port", "String", "7860", "Port"),
        ],
        homepage="https://github.com/cocktailpeanut/fluxgym",
        is_training=True,
    ),

    "StableSwarmUI": PackageDef(
        name="StableSwarmUI",
        display_name="StableSwarmUI",
        author="mcmonkeyprojects",
        github_repo="mcmonkeyprojects/StableSwarmUI",
        branch="master",
        description="Modularer WebUI mit Swarm-Architektur, unterstuetzt ComfyUI als Backend.",
        launch_script="launch-windows.bat",
        color="#b4befe",
        icon="◆",
        tags=["webui", "swarm"],
        shared_folders=[
            SharedFolderRule("StableDiffusion", "Models/Stable-Diffusion"),
            SharedFolderRule("LORA",            "Models/Lora"),
            SharedFolderRule("VAE",             "Models/VAE"),
            SharedFolderRule("ControlNet",      "Models/controlnet"),
        ],
        launch_options=[
            LaunchOption("--port",   "String", "7801","Port"),
            LaunchOption("--listen", "Bool",   False, "Oeffentlich erreichbar"),
        ],
        homepage="https://github.com/mcmonkeyprojects/StableSwarmUI",
    ),

    "Wan2GP": PackageDef(
        name="Wan2GP",
        display_name="Wan2GP (Video)",
        author="deepbeepmeep",
        github_repo="deepbeepmeep/Wan2GP",
        branch="main",
        description="Wan2.1 Video-Generierung mit GPU-Optimierungen fuer Verbraucher-Hardware.",
        launch_script="app.py",
        color="#f5c2e7",
        icon="◆",
        tags=["video", "wan"],
        shared_folders=[
            SharedFolderRule("Diffusers", "models/Wan2.1"),
        ],
        launch_options=[
            LaunchOption("--port",   "String", "7860","Port"),
            LaunchOption("--listen", "Bool",   False, "Alle Interfaces"),
        ],
        homepage="https://github.com/deepbeepmeep/Wan2GP",
    ),

    "framepack": PackageDef(
        name="framepack",
        display_name="FramePack (Video)",
        author="lllyasviel",
        github_repo="lllyasviel/FramePack",
        branch="main",
        description="FramePack — Video-Generierung Frame-fuer-Frame, sehr speichereffizient.",
        launch_script="demo_gradio.py",
        color="#f5e0dc",
        icon="◆",
        tags=["video"],
        shared_folders=[
            SharedFolderRule("Diffusers", "hf_download"),
        ],
        launch_options=[
            LaunchOption("--port",   "String", "7860","Port"),
            LaunchOption("--listen", "Bool",   False, "Alle Interfaces"),
        ],
        homepage="https://github.com/lllyasviel/FramePack",
    ),
}

# ── Hilfsfunktionen ──────────────────────────────────────────────────

def get_package(name: str) -> Optional[PackageDef]:
    """Gibt Package-Definition per Name zurueck (case-insensitive)."""
    if name in PACKAGE_CATALOG:
        return PACKAGE_CATALOG[name]
    name_lower = name.lower()
    for k, v in PACKAGE_CATALOG.items():
        if k.lower() == name_lower or v.display_name.lower() == name_lower:
            return v
    return None


def get_by_tags(tags: list[str]) -> list[PackageDef]:
    """Filtert Pakete nach Tags."""
    result = []
    for pkg in PACKAGE_CATALOG.values():
        if any(t in pkg.tags for t in tags):
            result.append(pkg)
    return result


def get_webui_packages() -> list[PackageDef]:
    return [p for p in PACKAGE_CATALOG.values() if not p.is_training]


def get_training_packages() -> list[PackageDef]:
    return [p for p in PACKAGE_CATALOG.values() if p.is_training]
