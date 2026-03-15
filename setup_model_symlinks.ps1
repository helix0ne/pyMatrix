# ============================================================
# Universelles SD-Modell Symlink-Setup
# Als Administrator ausfuehren!
# ============================================================
#
# Erstellt eine gemeinsame Modellbibliothek und verknuepft
# alle WebUI-Modellordner per Symlinks darauf.
#
# NUTZUNG:
#   1. Pfade unten anpassen ($MASTER_DIR und $SM_PACKAGES)
#   2. PowerShell als Administrator starten
#   3. Ausfuehren: .\setup_model_symlinks.ps1 -DryRun
#   4. Wenn alles passt: .\setup_model_symlinks.ps1
#
# WICHTIG: Vorher Modelle sichern!
# ============================================================

param(
    [string]$MASTER_DIR = "D:\Programme\stability_matrix\models",
    [string]$SM_PACKAGES = "D:\Programme\stability_matrix\Packages",
    [switch]$DryRun = $false,
    [switch]$Force = $false
)

# === Master-Verzeichnisse ===

$masterFolders = @(
    # Kern-Diffusion
    "checkpoints",
    "checkpoints\SD1.5",
    "checkpoints\SDXL",
    "checkpoints\PONY",
    "checkpoints\FLUX",
    "checkpoints\WAN",
    "checkpoints\SVD",
    "diffusion_models",
    "diffusers",

    # Encoder / Decoder
    "clip",
    "clip_vision",
    "text_encoders",
    "unet",
    "vae",
    "vae_approx",

    # Adapter
    "loras",
    "loras\SDXL",
    "loras\SDXL\Background",
    "loras\SDXL\Character",
    "loras\SDXL\Clothing",
    "loras\SDXL\Concept",
    "loras\SDXL\Objects",
    "loras\SDXL\Poses",
    "loras\SDXL\Style",
    "loras\SDXL\Tool",
    "loras\SD1.5",
    "loras\SD1.5\Background",
    "loras\SD1.5\Clothing",
    "loras\SD1.5\Pony",
    "loras\SD1.5\Poses",
    "loras\SD1.5\Tool",
    "loras\Flux",
    "lycoris",
    "hypernetworks",

    # Steuerung
    "controlnet",
    "controlnet\canny",
    "controlnet\depth",
    "controlnet\lineart",
    "controlnet\MLSD",
    "controlnet\normalbae",
    "controlnet\openpose",
    "controlnet\scribble",
    "controlnet\seg",
    "controlnet\softedge",
    "controlnet\tile",
    "controlnet\union",
    "ipadapter",
    "ipadapter\sd15",
    "ipadapter\sdxl",
    "t2i_adapter",

    # Prompt / Embedding
    "embeddings",

    # Upscaler
    "upscalers",
    "upscalers\AnimeSharp",
    "upscalers\ESRGAN",
    "upscalers\foolhardy",
    "upscalers\NMKD",
    "upscalers\RealESRGAN",
    "upscalers\ScuNET",
    "upscalers\SRFormer",
    "upscalers\SwinIR",
    "upscalers\UltraSharp",

    # Gesichtsrestaurierung
    "face_models",
    "face_models\CodeFormer",
    "face_models\GFPGAN",

    # Erkennung / Analyse
    "detection",
    "detection\BLIP",
    "detection\DeepDanbooru",
    "detection\DepthAnything",
    "detection\SAM",
    "detection\Ultralytics",
    "detection\Ultralytics\bbox",
    "detection\Ultralytics\segm",
    "detection\Ultralytics\yolov",
    "pose",
    "pose\OpenPose",

    # Spezial
    "ic-light",
    "inswapper",
    "Deoldify",
    "Reactor",
    "nsfw_detector",
    "photomaker",
    "style_models",
    "audio_encoders",
    "gligen",
    "motion",

    # Video
    "video",
    "video\cogvideo",

    # Sonstiges
    "workflows"
)

# === Symlink-Definitionen ===
# Format: "Paketname|Ziel-Pfad-relativ|Master-Pfad-relativ"

$symlinkMap = @(
    # --- ComfyUI ---
    "ComfyUI|models\checkpoints|checkpoints",
    "ComfyUI|models\diffusion_models|diffusion_models",
    "ComfyUI|models\clip|clip",
    "ComfyUI|models\clip_vision|clip_vision",
    "ComfyUI|models\text_encoders|text_encoders",
    "ComfyUI|models\unet|unet",
    "ComfyUI|models\vae|vae",
    "ComfyUI|models\vae_approx|vae_approx",
    "ComfyUI|models\loras|loras",
    "ComfyUI|models\controlnet|controlnet",
    "ComfyUI|models\ipadapter|ipadapter",
    "ComfyUI|models\embeddings|embeddings",
    "ComfyUI|models\upscale_models|upscalers",
    "ComfyUI|models\style_models|style_models",
    "ComfyUI|models\audio_encoders|audio_encoders",
    "ComfyUI|models\gligen|gligen",
    "ComfyUI|models\hypernetworks|hypernetworks",
    "ComfyUI|models\photomaker|photomaker",
    "ComfyUI|models\diffusers|diffusers",

    # --- Forge ---
    "stable-diffusion-webui-forge|models\Stable-diffusion|checkpoints",
    "stable-diffusion-webui-forge|models\Lora|loras",
    "stable-diffusion-webui-forge|models\LyCORIS|lycoris",
    "stable-diffusion-webui-forge|models\ControlNet|controlnet",
    "stable-diffusion-webui-forge|models\VAE|vae",
    "stable-diffusion-webui-forge|models\ESRGAN|upscalers\ESRGAN",
    "stable-diffusion-webui-forge|models\RealESRGAN|upscalers\RealESRGAN",
    "stable-diffusion-webui-forge|models\SwinIR|upscalers\SwinIR",
    "stable-diffusion-webui-forge|models\GFPGAN|face_models\GFPGAN",
    "stable-diffusion-webui-forge|models\CodeFormer|face_models\CodeFormer",
    "stable-diffusion-webui-forge|models\BLIP|detection\BLIP",
    "stable-diffusion-webui-forge|models\IPAdapter|ipadapter",
    "stable-diffusion-webui-forge|models\T2I-Adapter|t2i_adapter",
    "stable-diffusion-webui-forge|models\clip|clip",
    "stable-diffusion-webui-forge|models\clip_vision|clip_vision",
    "stable-diffusion-webui-forge|models\text_encoder|text_encoders",
    "stable-diffusion-webui-forge|models\unet|unet",
    "stable-diffusion-webui-forge|embeddings|embeddings",
    "stable-diffusion-webui-forge|models\hypernetworks|hypernetworks",

    # --- ReForge ---
    "stable-diffusion-webui-reForge|models\Stable-diffusion|checkpoints",
    "stable-diffusion-webui-reForge|models\Lora|loras",
    "stable-diffusion-webui-reForge|models\LyCORIS|lycoris",
    "stable-diffusion-webui-reForge|models\ControlNet|controlnet",
    "stable-diffusion-webui-reForge|models\VAE|vae",
    "stable-diffusion-webui-reForge|models\ESRGAN|upscalers\ESRGAN",
    "stable-diffusion-webui-reForge|models\RealESRGAN|upscalers\RealESRGAN",
    "stable-diffusion-webui-reForge|models\GFPGAN|face_models\GFPGAN",
    "stable-diffusion-webui-reForge|models\CodeFormer|face_models\CodeFormer",
    "stable-diffusion-webui-reForge|models\BLIP|detection\BLIP",
    "stable-diffusion-webui-reForge|models\clip|clip",
    "stable-diffusion-webui-reForge|models\unet|unet",
    "stable-diffusion-webui-reForge|embeddings|embeddings",

    # --- A1111 ---
    "stable-diffusion-webui|models\Stable-diffusion|checkpoints",
    "stable-diffusion-webui|models\Lora|loras",
    "stable-diffusion-webui|models\LyCORIS|lycoris",
    "stable-diffusion-webui|models\ControlNet|controlnet",
    "stable-diffusion-webui|models\VAE|vae",
    "stable-diffusion-webui|models\ESRGAN|upscalers\ESRGAN",
    "stable-diffusion-webui|models\RealESRGAN|upscalers\RealESRGAN",
    "stable-diffusion-webui|models\GFPGAN|face_models\GFPGAN",
    "stable-diffusion-webui|models\CodeFormer|face_models\CodeFormer",
    "stable-diffusion-webui|models\BLIP|detection\BLIP",
    "stable-diffusion-webui|embeddings|embeddings",
    "stable-diffusion-webui|models\hypernetworks|hypernetworks",

    # --- SD.Next ---
    "sdnext|models\Stable-diffusion|checkpoints",
    "sdnext|models\diffusers|diffusers",
    "sdnext|models\unet|unet",
    "sdnext|models\clip|clip",
    "sdnext|models\clip_vision|clip_vision",
    "sdnext|models\text_encoder|text_encoders",
    "sdnext|models\lora|loras",
    "sdnext|models\lycoris|lycoris",
    "sdnext|models\controlnet|controlnet",
    "sdnext|models\vae|vae",
    "sdnext|models\hypernetworks|hypernetworks",
    "sdnext|models\ipadapter|ipadapter",
    "sdnext|embeddings|embeddings",

    # --- Fooocus ---
    "Fooocus|models\checkpoints|checkpoints",
    "Fooocus|models\loras|loras",
    "Fooocus|models\vae|vae",
    "Fooocus|models\controlnet|controlnet",
    "Fooocus|models\embeddings|embeddings",
    "Fooocus|models\upscalers|upscalers",

    # --- InvokeAI ---
    "invokeai|models\checkpoints|checkpoints",
    "invokeai|models\diffusers|diffusers",
    "invokeai|models\vae|vae",
    "invokeai|models\loras|loras",
    "invokeai|models\controlnet|controlnet",
    "invokeai|models\ip_adapter|ipadapter",
    "invokeai|models\embeddings|embeddings",

    # --- StableSwarmUI ---
    "StableSwarmUI|models\checkpoints|checkpoints",
    "StableSwarmUI|models\loras|loras",
    "StableSwarmUI|models\vae|vae",
    "StableSwarmUI|models\controlnet|controlnet",

    # --- VoltaML ---
    "VoltaML|models\checkpoints|checkpoints",
    "VoltaML|models\loras|loras",
    "VoltaML|models\vae|vae",
    "VoltaML|models\controlnet|controlnet",
    "VoltaML|models\upscalers|upscalers",

    # --- Kohya GUI ---
    "kohya_gui|models\checkpoints|checkpoints",
    "kohya_gui|models\vae|vae"
)

# === Hilfsfunktionen ===

function Write-Status($msg, $color = "White") {
    Write-Host $msg -ForegroundColor $color
}

function Create-Symlink($linkPath, $targetPath) {
    if ($DryRun) {
        Write-Status "  [VORSCHAU] mklink /D `"$linkPath`" -> `"$targetPath`"" "Yellow"
        return
    }

    if (Test-Path $linkPath) {
        $item = Get-Item $linkPath -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            Write-Status "  [SKIP] Bereits verknuepft: $linkPath" "DarkGray"
            return
        }
        if ($Force) {
            Write-Status "  [VERSCHIEBE] Vorhandene Dateien von $linkPath nach $targetPath" "Yellow"
            Get-ChildItem $linkPath -Force | Move-Item -Destination $targetPath -Force
            Remove-Item $linkPath -Recurse -Force
        } else {
            Write-Status "  [WARNUNG] Verzeichnis existiert (nutze -Force zum Zusammenfuehren): $linkPath" "Red"
            return
        }
    }

    $parent = Split-Path $linkPath -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    cmd /c mklink /D "$linkPath" "$targetPath" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Status "  [OK] $linkPath -> $targetPath" "Green"
    } else {
        Write-Status "  [FEHLER] Symlink konnte nicht erstellt werden (als Admin ausfuehren!): $linkPath" "Red"
    }
}

# === HAUPTPROGRAMM ===

Write-Status ""
Write-Status "========================================" "Cyan"
Write-Status " SD Universelles Modell-Symlink Setup" "Cyan"
Write-Status "========================================" "Cyan"
Write-Status ""
Write-Status "Master-Verzeichnis: $MASTER_DIR"
Write-Status "Pakete-Verzeichnis: $SM_PACKAGES"
if ($DryRun) { Write-Status "[VORSCHAU-MODUS - keine Aenderungen]" "Yellow" }
Write-Status ""

# Schritt 1: Master-Verzeichnisse erstellen
Write-Status "Erstelle Master-Modellverzeichnisse..." "Cyan"
foreach ($folder in $masterFolders) {
    $path = Join-Path $MASTER_DIR $folder
    if (-not (Test-Path $path)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
        Write-Status "  [ERSTELLT] $path" "Green"
    }
}

# Schritt 2: Symlinks fuer jedes Paket erstellen
Write-Status ""
Write-Status "Erstelle Symlinks fuer WebUI-Pakete..." "Cyan"

$currentPackage = ""
foreach ($entry in $symlinkMap) {
    $parts = $entry.Split("|")
    $package = $parts[0]
    $relTarget = $parts[1]
    $relMaster = $parts[2]

    $packageDir = Join-Path $SM_PACKAGES $package

    if (-not (Test-Path $packageDir) -and -not $DryRun) {
        if ($package -ne $currentPackage) {
            Write-Status "  [SKIP] Paket nicht gefunden: $package" "DarkGray"
            $currentPackage = $package
        }
        continue
    }

    if ($package -ne $currentPackage) {
        Write-Status ""
        Write-Status "  >> $package" "Magenta"
        $currentPackage = $package
    }

    $linkPath = Join-Path $packageDir $relTarget
    $masterPath = Join-Path $MASTER_DIR $relMaster

    Create-Symlink $linkPath $masterPath
}

Write-Status ""
Write-Status "========================================" "Cyan"
Write-Status " Fertig!" "Green"
Write-Status "========================================" "Cyan"
Write-Status ""
Write-Status "Hinweise:" "Yellow"
Write-Status "  - Nutze -DryRun um Aenderungen nur anzuzeigen"
Write-Status "  - Nutze -Force um vorhandene Dateien in Master-Verzeichnis zu verschieben"
Write-Status "  - Passe `$SM_PACKAGES an wenn deine Pakete woanders liegen"
Write-Status ""
