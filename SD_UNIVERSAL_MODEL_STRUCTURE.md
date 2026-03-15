# Universelle Stable Diffusion Modell-Struktur
# Kompatibilitaet: Alle wichtigen WebUIs via StabilityMatrix

> Erstellt: 14.03.2026
> Quelle: TreeSize-Exports, StabilityMatrix-Screenshots, CivitAI-Taxonomie
> Installation: D:\Programme\stability_matrix\

---

# TEIL A: TAXONOMIE

## A1. Basismodell-Architekturen (40+ Varianten)

Jede Architektur definiert: Checkpoint, Text-Encoder, UNet, VAE.

### Bildgenerierung

| Familie | Varianten | Status |
|---------|-----------|--------|
| **SD 1.x** | SD 1.4, SD 1.5, SD 1.5 LCM, SD 1.5 Hyper | Stabil, weit verbreitet |
| **SD 2.x** | SD 2.0, SD 2.1 | Veraltet, selten genutzt |
| **SDXL** | SDXL 1.0, SDXL Lightning, SDXL Hyper | Standard fuer hochaufloesende Bilder |
| **Pony** | Pony, Pony V7 | Anime/Illustration-Fokus |
| **Illustrious** | Illustrious | Anime-Fokus |
| **NoobAI** | NoobAI | Community-Modell |
| **Flux** | Flux .1 S, Flux .1 D, Flux .1 Krea, Flux .1 Kontext, Flux .2 D, Flux .2 Klein 9B, Flux .2 Klein 9B-base, Flux .2 Klein 4B, Flux .2 Klein 4B-base | Neue Generation, wachsend |
| **PixArt** | PixArt alpha, PixArt Sigma | Schnelle Inferenz |
| **Hunyuan** | Hunyuan 1 | Tencent, mehrsprachig |
| **Sonstige** | Chroma, HiDream, Kolors, Lumina, Anima, Aura Flow, Qwen, Z Image Turbo, Z Image Base | Nischen/experimentell |

### Videogenerierung

| Familie | Varianten |
|---------|-----------|
| **Wan Video** | 1.3B t2v, 14B t2v, 14B i2v 480p, 14B i2v 720p, 2.2 TI2V-5B, 2.2 I2V-A14B, 2.2 T2V-A14B, 2.5 T2V, 2.5 I2V |
| **Hunyuan Video** | Hunyuan Video |
| **CogVideoX** | CogVideoX |
| **Sonstige** | Mochi, LTXV, LTXV2 |

---

## A2. Modelltypen (16 funktionale Klassen)

Aus CivitAI / StabilityMatrix UI extrahiert.

### Kern-Diffusion

| Typ | Beschreibung | Dateiformat | Ordnername |
|-----|-------------|-------------|------------|
| Checkpoint | Zusammengefuehrtes Modell (UNet+VAE+CLIP) | .safetensors, .ckpt | checkpoints / Stable-diffusion |
| UNet | Nur Denoising-Netzwerk | .safetensors | unet |
| VAE | Variational Autoencoder | .safetensors, .pt | vae / VAE |
| VAE Approx | Schnelle VAE-Vorschau | .pt | vae_approx / ApproxVAE |
| Text Encoder | Text-zu-Embedding | .safetensors | text_encoders / TextEncoders |
| CLIP | CLIP Text-Encoder | .safetensors | clip |
| CLIP Vision | CLIP Bild-Encoder | .safetensors | clip_vision / ClipVision |
| Diffusion Models | Standalone-Diffusionsmodell | .safetensors | diffusion_models |
| Diffusers | HuggingFace-Format | Verzeichnis | diffusers / Diffusers |

### Adapter und Erweiterungen

| Typ | Beschreibung | Ordnername |
|-----|-------------|------------|
| LoRA | Low-Rank Adaptation | loras / Lora |
| LyCORIS | LoHA, LoKr, DyLoRA etc. | lycoris / LyCORIS |
| DoRA | Weight-Decomposed LoRA | dora |
| ControlNet | Bedingte Steuerung (Canny, Depth, Pose...) | controlnet / ControlNet |
| IP-Adapter | Bild-Prompt Adapter | ipadapter / IpAdapter / IPAdapter |
| T2I-Adapter | Text-zu-Bild Adapter | t2i_adapter / T2I-Adapter |
| Hypernetwork | Hypernetwork Fine-Tuning | hypernetworks / Hypernetwork |
| Aesthetic Gradient | Aesthetik-Steuerung | - |
| Motion | AnimateDiff / Bewegungsmodule | motion |

### Prompt und Embedding

| Typ | Beschreibung | Ordnername |
|-----|-------------|------------|
| Embedding | Textual Inversion | embeddings / Embeddings |
| Wildcards | Prompt-Platzhalter | wildcards |

### Nachbearbeitung

| Typ | Beschreibung | Ordnername |
|-----|-------------|------------|
| ESRGAN | Upscaler | ESRGAN |
| RealESRGAN | Upscaler (realistisch) | RealESRGAN |
| SwinIR | Upscaler | SwinIR |
| ScuNET | Denoiser/Upscaler | ScuNET |
| UltraSharp | Upscaler | UltraSharp |
| SRFormer | Upscaler | SRFormer |
| NMKD | Upscaler | NMKD |
| AnimeSharp | Upscaler (Anime) | AnimeSharp |
| foolhardy | Upscaler | foolhardy |

### Gesichtsrestaurierung

| Typ | Beschreibung | Ordnername |
|-----|-------------|------------|
| GFPGAN | Gesichtswiederherstellung | GFPGAN |
| CodeFormer | Gesichtswiederherstellung | Codeformer |

### Erkennung und Analyse

| Typ | Beschreibung | Ordnername |
|-----|-------------|------------|
| DeepDanbooru | Anime-Tag-Erkennung | DeepDanbooru |
| Ultralytics/YOLO | Objekterkennung | Ultralytics (yolov, segm, bbox) |
| BLIP | Bildbeschriftung | BLIP |
| SAM | Segment Anything | Sams |
| OpenPose | Posenerkennung | Openpose / OpenPose |
| DepthAnything | Tiefenschaetzung | depthanything |

### Spezial

| Typ | Beschreibung | Ordnername |
|-----|-------------|------------|
| ic-light | Beleuchtungssteuerung | ic-light |
| inswapper | Gesichtertausch | inswapper |
| Deoldify | Kolorierung alter Fotos | Deoldify |
| Reactor | Gesichtertausch | Reactor |
| nsfw_detector | NSFW-Erkennung | nsfw_detector |
| pyannote | Audio/Sprecheridentifikation | pyannote |
| Style Models | Stiltransfer | style_models |
| Audio Encoders | Audiokodierung | audio_encoders |
| GLIGEN | Raeumliche Steuerung | gligen / GLIGEN |
| Photomaker | Gesichtsgenerierung | photomaker |

---

# TEIL B: WEBUI-VERZEICHNISSTRUKTUREN (16 UIs)

## B1. A1111-Familie

Gilt fuer: **Automatic1111, Forge, ReForge, AMDGPU Forge, DirectML**

```
stable-diffusion-webui/
├── models/
│   ├── Stable-diffusion/        # Checkpoints
│   ├── Lora/
│   ├── LyCORIS/
│   ├── ControlNet/
│   ├── VAE/
│   ├── hypernetworks/
│   ├── ESRGAN/
│   ├── RealESRGAN/
│   ├── SwinIR/
│   ├── GFPGAN/
│   ├── CodeFormer/
│   ├── BLIP/
│   ├── T2I-Adapter/             # nur Forge
│   ├── IPAdapter/               # nur Forge
│   ├── clip/                    # nur Forge
│   ├── clip_vision/             # nur Forge
│   ├── text_encoder/            # nur Forge
│   └── unet/                    # nur Forge
├── embeddings/
├── extensions/
├── scripts/
└── outputs/
```

## B2. SD.Next

```
sdnext/
├── models/
│   ├── Stable-diffusion/
│   ├── diffusers/
│   ├── unet/
│   ├── clip/
│   ├── clip_vision/
│   ├── text_encoder/
│   ├── lora/
│   ├── lycoris/
│   ├── controlnet/
│   ├── vae/
│   ├── hypernetworks/
│   └── ipadapter/
├── embeddings/
└── extensions/
```

## B3. SD WebUI-UX

```
sd-webui-ux/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── vae/
│   ├── controlnet/
│   └── embeddings/
└── outputs/
```

## B4. Fooocus-Familie

Gilt fuer: **Fooocus, Fooocus MRE, Fooocus ControlNet SDXL, Ruined Fooocus, mashb1t 1-Up**

```
Fooocus/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── vae/
│   ├── controlnet/
│   ├── embeddings/
│   └── upscalers/
├── wildcards/
└── outputs/
```

## B5. SimpleSDXL

```
SimpleSDXL/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── vae/
│   ├── controlnet/
│   └── refiner/
```

## B6. ComfyUI

Umfangreichste Struktur (Node-basiert).

```
ComfyUI/
├── models/
│   ├── checkpoints/
│   ├── diffusion_models/
│   ├── clip/
│   ├── clip_vision/
│   ├── text_encoders/
│   ├── unet/
│   ├── vae/
│   ├── vae_approx/
│   ├── loras/
│   ├── controlnet/
│   ├── ipadapter/
│   ├── embeddings/
│   ├── upscale_models/
│   ├── style_models/
│   ├── audio_encoders/
│   ├── gligen/
│   ├── latent_upscale_models/
│   ├── model_patches/
│   └── photomaker/
├── custom_nodes/
├── input/
└── output/
```

## B7. StableSwarmUI

```
StableSwarmUI/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── vae/
│   └── controlnet/
├── workflows/
└── swarm/
```

## B8. VoltaML

```
VoltaML/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── vae/
│   ├── controlnet/
│   └── upscalers/
├── pipelines/
└── outputs/
```

## B9. InvokeAI

```
invokeai/
├── models/
│   ├── checkpoints/
│   ├── diffusers/
│   ├── vae/
│   ├── loras/
│   ├── controlnet/
│   ├── ip_adapter/
│   └── embeddings/
└── outputs/
```

## B10. SDFX

```
SDFX/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── controlnet/
│   └── vae/
└── workflows/
```

## B11. Kohya GUI (Training)

```
kohya_gui/
├── models/
│   ├── checkpoints/
│   └── vae/
├── datasets/
├── output/
└── logs/
```

## B12. OneTrainer (Training)

```
OneTrainer/
├── models/
│   ├── base_models/
│   └── loras/
├── datasets/
└── outputs/
```

## B13. FluxGym (Training)

```
FluxGym/
├── models/
│   ├── flux/
│   ├── clip/
│   └── vae/
└── datasets/
```

## B14. CogVideo / CogStudio (Video)

```
CogStudio/
├── models/
│   ├── cogvideo/
│   ├── text_encoder/
│   └── vae/
└── outputs/
```

---

## B15. Ordnernamen-Vergleichsmatrix

Welche UI welchen Ordnernamen fuer denselben Modelltyp verwendet:

| Modelltyp | A1111/Forge | SD.Next | ComfyUI | Fooocus | InvokeAI | SM Global |
|-----------|-------------|---------|---------|---------|----------|-----------|
| Checkpoint | Stable-diffusion | Stable-diffusion | checkpoints | checkpoints | checkpoints | Checkpoints |
| LoRA | Lora | lora | loras | loras | loras | Lora |
| LyCORIS | LyCORIS | lycoris | - | - | - | LyCORIS |
| VAE | VAE | vae | vae | vae | vae | VAE |
| ControlNet | ControlNet | controlnet | controlnet | controlnet | controlnet | ControlNet |
| Embedding | embeddings/ | embeddings/ | embeddings | embeddings | embeddings | Embeddings |
| CLIP | clip | clip | clip | - | - | - |
| CLIP Vision | clip_vision | clip_vision | clip_vision | - | - | ClipVision |
| Text Encoder | text_encoder | text_encoder | text_encoders | - | - | TextEncoders |
| UNet | unet | unet | unet | - | - | - |
| IP-Adapter | IPAdapter | ipadapter | ipadapter | - | ip_adapter | IpAdapter |
| T2I-Adapter | T2I-Adapter | - | - | - | - | T2IAdapter |
| Upscaler | ESRGAN | - | upscale_models | upscalers | - | ESRGAN etc. |
| Diffusers | - | diffusers | - | - | diffusers | Diffusers |
| Hypernetwork | hypernetworks | hypernetworks | hypernetworks | - | - | hypernetworks |

---

# TEIL C: DEINE INSTALLATION

## C1. Uebersicht

```
Laufwerk D:\ (931,5 GB, ~517 GB belegt, ~414 GB frei)

D:\Programme\stability_matrix\              <- Aktive Installation
├── models\          300,5 GB               <- Globale Modellbibliothek
└── Packages\
    └── ComfyUI\
        └── models\  23,5 KB               <- Alles Symlinks

D:\Programme\StabilityMatrix\Data\          <- Aeltere/zweite Installation
├── Assets\          73,5 GB
└── [Packages + Daten]  520,5 GB gesamt
```

---

## C2. Globale Modellbibliothek (sortiert nach Groesse)

**Pfad:** `D:\Programme\stability_matrix\models\`
**Gesamt:** 300,5 GB | 7.616 Dateien | 189 Verzeichnisse

### Kern-Modelle (288,2 GB = 96%)

| Ordner | Groesse | Inhalt |
|--------|---------|--------|
| **Checkpoints/** | 128,1 GB | Alle Basis-Modelle |
| - PONY/ | 45,4 GB | Pony-Checkpoints |
| - FLUX/ | 41,7 GB | Flux-Checkpoints |
| - SDXL/ | 32,5 GB | 27 SDXL-Modelle (+ base/, refiner/ leer) |
| - SD1.5/ | 8,5 GB | SD 1.5 Checkpoints |
| - WAN/ | 163 B | Nur Platzhalter |
| - SVD/ | 0 B | Leer |
| **Lora/** | 114,0 GB | Alle LoRA-Modelle |
| - SDXL/ | 67,9 GB | SDXL-LoRAs |
| -- Poses/ | 27,8 GB | Posen-LoRAs |
| -- Style/ | 16,3 GB | Stil-LoRAs |
| -- Tool/ | 14,7 GB | Werkzeug-LoRAs |
| -- Neu/ | 8,9 GB | Neue/unsortierte |
| -- Clothing/ | 141,5 MB | Kleidung |
| -- Background/ | 70,3 MB | Hintergruende |
| -- Character/ | 26,9 MB | Charaktere |
| -- Concept/ | 14,4 MB | Konzepte |
| -- Objects/ | 0 B | Leer |
| - SD1.5/ | 44,0 GB | SD 1.5 LoRAs |
| -- [1220 Dateien] | 16,0 GB | Unsortiert |
| -- Clothing/ | 15,4 GB | Kleidung |
| -- Background/ | 4,8 GB | Hintergruende |
| -- Tool/ | 4,5 GB | Werkzeuge |
| -- Poses/ | 3,4 GB | Posen |
| -- Pony/ | 2,1 GB | Pony-LoRAs |
| - Flux/ | 0 B | Leer |
| **TextEncoders/** | 28,6 GB | CLIP/T5-Encoder |
| **VAE/** | 10,6 GB | VAE-Modelle |
| **ControlNet/** | 6,9 GB | Steuerungsmodelle |
| - controlnet-union-sdxl-1.0/ | 4,8 GB | Union-Modell |
| - lineart/ | 1,3 GB | Linienkunst |
| - depth/, MLSD/, softedge/ | ~9 MB | Tiefe, Kanten |
| - openpose/ | 1,0 MB | Posen |
| - T2IAdapter/ | 1,0 MB | T2I-Adapter (10 Varianten) |

### Erkennung und Analyse (3,9 GB)

| Ordner | Groesse |
|--------|---------|
| BLIP/ | 854,6 MB |
| Ultralytics/ | 735,9 MB (yolov 683,6 + segm 52,3) |
| DeepDanbooru/ | 614,3 MB |
| Sams/ | 506,4 MB |
| depthanything/ | 371,8 MB |
| DiffusionModels/u2net/ | 335,7 MB |
| nsfw_detector/ | 328,5 MB |
| Openpose/ | 43,6 MB |

### Upscaler (1,3 GB)

| Ordner | Groesse |
|--------|---------|
| SRFormer/ | 751,1 MB |
| NMKD/ | 223,5 MB |
| RealESRGAN/ | 129,2 MB |
| ScuNET/ | 68,6 MB |
| UltraSharp/ | 64,5 MB |
| foolhardy/ | 64,1 MB |
| AnimeSharp/ | 63,9 MB |
| ESRGAN/ | 30,1 MB |

### Gesichtsrestaurierung und Spezial (7,0 GB)

| Ordner | Groesse |
|--------|---------|
| ic-light/ | 3,2 GB |
| inswapper/ | 1,6 GB |
| Deoldify/ | 1,3 GB |
| LyCORIS/ | 510,3 MB |
| Embeddings/ | 469,7 MB |
| ClipVision/ | 440,7 MB |
| Codeformer/ | 359,2 MB |
| alignment/det_align/ | 178,2 MB |
| GFPGAN/ | 161,5 MB |
| ApproxVAE/ | 25,0 MB |
| IpAdapter/ | 16,1 MB (XL 8,3 + SD1.5 7,8) |

### Sonstige (< 100 MB)

| Ordner | Groesse |
|--------|---------|
| __LLM/ | 85,9 MB (LLM-Modelle - gehoert hier nicht hin) |
| pyannote/ | 31,0 MB |
| Reactor/faces/ | 1,1 MB |
| loras_i2v/ | 13,4 KB |
| Karlo/ | 6,9 KB |
| Diffusers/ | 2 B |

### Leere Platzhalter-Verzeichnisse (0 B)

Alphabetisch sortiert. Viele davon sind Duplikate oder veraltet:

```
AfterDetailer/          LDSR/
BSRGAN/                 PromptExpansion/
clip_vision/            Stable-diffusion/
ClipVision/ (Duplikat)  StableDiffusion/
Codeformer/ (Duplikat)  SVD/
ControlNetPreprocessor/ SwinIR/
GLIGEN/                 T2IAdapter/ (Duplikat)
Hypernetwork/           t2iadapter_*/ (10 Stueck)
hypernetworks/          t2i-adapter-*/ (6 Stueck)
IpAdapter/ (Duplikat)
IpAdapters15/ (Duplikat)
IpAdaptersXl/ (Duplikat)
ip_adapter_sd15_light/
```

---

## C3. ComfyUI-Symlinks

**Pfad:** `D:\Programme\stability_matrix\Packages\ComfyUI\models\`
**Groesse:** 23,5 KB (nur configs/ hat Daten, alles andere = Symlinks)

```
audio_encoders/         -> global    latent_upscale_models/  -> global
checkpoints/            -> global    loras/                  -> global
clip/                   -> global    model_patches/          -> global
clip_vision/            -> global    photomaker/             -> global
configs/                23,5 KB      style_models/           -> global
controlnet/             -> global    text_encoders/          -> global
diffusers/              -> global    unet/                   -> global
diffusion_models/       -> global    upscale_models/         -> global
embeddings/             -> global    vae/                    -> global
gligen/                 -> global    vae_approx/             -> global
hypernetworks/          -> global
```

---

## C4. StabilityMatrix Data-Verzeichnis

**Pfad:** `D:\Programme\StabilityMatrix\Data\`
**Gesamt:** 520,5 GB

```
Data/                                520,5 GB
├── .downloads/
├── Assets/                           73,5 GB
│   ├── checkpoints/
│   ├── clip/
│   ├── controlnet/
│   ├── duplicates/
│   ├── embeddings/
│   ├── facerestore/
│   ├── ipadapter/
│   ├── lora/
│   └── nodejs/                       78,9 MB (eingebettete Runtime)
└── [Packages + weitere Daten]
```

---

# TEIL D: UNIVERSELLE MASTER-STRUKTUR

## D1. Ideale globale Modellbibliothek

Alle WebUIs greifen per Symlinks auf einen einzigen Ordner zu.

```
AI_MODELS/
│
│   === KERN-DIFFUSION ===
├── checkpoints/
│   ├── SD1.5/
│   ├── SDXL/
│   ├── PONY/
│   ├── FLUX/
│   ├── WAN/
│   └── SVD/
├── diffusion_models/
├── diffusers/
│
│   === ENCODER / DECODER ===
├── clip/
├── clip_vision/
├── text_encoders/
├── unet/
├── vae/
├── vae_approx/
│
│   === ADAPTER ===
├── loras/
│   ├── SDXL/
│   │   ├── Background/
│   │   ├── Character/
│   │   ├── Clothing/
│   │   ├── Concept/
│   │   ├── Objects/
│   │   ├── Poses/
│   │   ├── Style/
│   │   └── Tool/
│   ├── SD1.5/
│   │   ├── Background/
│   │   ├── Clothing/
│   │   ├── Pony/
│   │   ├── Poses/
│   │   └── Tool/
│   └── Flux/
├── lycoris/
├── hypernetworks/
│
│   === STEUERUNG ===
├── controlnet/
│   ├── canny/
│   ├── depth/
│   ├── lineart/
│   ├── MLSD/
│   ├── normalbae/
│   ├── openpose/
│   ├── scribble/
│   ├── seg/
│   ├── softedge/
│   ├── tile/
│   └── union/
├── ipadapter/
│   ├── sd15/
│   └── sdxl/
├── t2i_adapter/
│
│   === PROMPT / EMBEDDING ===
├── embeddings/
│
│   === UPSCALER ===
├── upscalers/
│   ├── AnimeSharp/
│   ├── ESRGAN/
│   ├── foolhardy/
│   ├── NMKD/
│   ├── RealESRGAN/
│   ├── ScuNET/
│   ├── SRFormer/
│   ├── SwinIR/
│   └── UltraSharp/
│
│   === GESICHTSRESTAURIERUNG ===
├── face_models/
│   ├── CodeFormer/
│   └── GFPGAN/
│
│   === ERKENNUNG / ANALYSE ===
├── detection/
│   ├── BLIP/
│   ├── DeepDanbooru/
│   ├── DepthAnything/
│   ├── SAM/
│   └── Ultralytics/
│       ├── bbox/
│       ├── segm/
│       └── yolov/
├── pose/
│   └── OpenPose/
│
│   === SPEZIAL ===
├── ic-light/
├── inswapper/
├── Deoldify/
├── Reactor/
├── nsfw_detector/
├── photomaker/
├── style_models/
├── audio_encoders/
├── gligen/
├── motion/
│
│   === VIDEO ===
├── video/
│   └── cogvideo/
│
│   === SONSTIGES ===
└── workflows/
```

---

## D2. Symlink-Zuordnung (Master -> WebUI)

### A1111 / Forge / ReForge

```
MASTER                          ->  WebUI-Pfad
checkpoints/                    ->  models/Stable-diffusion
loras/                          ->  models/Lora
lycoris/                        ->  models/LyCORIS
controlnet/                     ->  models/ControlNet
vae/                            ->  models/VAE
upscalers/ESRGAN/               ->  models/ESRGAN
upscalers/RealESRGAN/           ->  models/RealESRGAN
upscalers/SwinIR/               ->  models/SwinIR
face_models/GFPGAN/             ->  models/GFPGAN
face_models/CodeFormer/         ->  models/CodeFormer
detection/BLIP/                 ->  models/BLIP
embeddings/                     ->  embeddings
hypernetworks/                  ->  hypernetworks
ipadapter/                      ->  models/IPAdapter         (nur Forge)
t2i_adapter/                    ->  models/T2I-Adapter       (nur Forge)
clip/                           ->  models/clip              (nur Forge)
clip_vision/                    ->  models/clip_vision       (nur Forge)
text_encoders/                  ->  models/text_encoder      (nur Forge)
unet/                           ->  models/unet              (nur Forge)
```

### ComfyUI

```
MASTER                          ->  ComfyUI-Pfad
checkpoints/                    ->  models/checkpoints
diffusion_models/               ->  models/diffusion_models
clip/                           ->  models/clip
clip_vision/                    ->  models/clip_vision
text_encoders/                  ->  models/text_encoders
unet/                           ->  models/unet
vae/                            ->  models/vae
vae_approx/                     ->  models/vae_approx
loras/                          ->  models/loras
controlnet/                     ->  models/controlnet
ipadapter/                      ->  models/ipadapter
embeddings/                     ->  models/embeddings
upscalers/ (zusammengefuehrt)   ->  models/upscale_models
style_models/                   ->  models/style_models
audio_encoders/                 ->  models/audio_encoders
gligen/                         ->  models/gligen
photomaker/                     ->  models/photomaker
```

### SD.Next

```
MASTER                          ->  SD.Next-Pfad
checkpoints/                    ->  models/Stable-diffusion
diffusers/                      ->  models/diffusers
unet/                           ->  models/unet
clip/                           ->  models/clip
clip_vision/                    ->  models/clip_vision
text_encoders/                  ->  models/text_encoder
loras/                          ->  models/lora
lycoris/                        ->  models/lycoris
controlnet/                     ->  models/controlnet
vae/                            ->  models/vae
hypernetworks/                  ->  models/hypernetworks
ipadapter/                      ->  models/ipadapter
embeddings/                     ->  embeddings
```

### Fooocus (alle Varianten)

```
MASTER                          ->  Fooocus-Pfad
checkpoints/                    ->  models/checkpoints
loras/                          ->  models/loras
vae/                            ->  models/vae
controlnet/                     ->  models/controlnet
embeddings/                     ->  models/embeddings
upscalers/ (zusammengefuehrt)   ->  models/upscalers
```

### InvokeAI

```
MASTER                          ->  InvokeAI-Pfad
checkpoints/                    ->  models/checkpoints
diffusers/                      ->  models/diffusers
vae/                            ->  models/vae
loras/                          ->  models/loras
controlnet/                     ->  models/controlnet
ipadapter/                      ->  models/ip_adapter
embeddings/                     ->  models/embeddings
```

### StableSwarmUI

```
MASTER                          ->  SwarmUI-Pfad
checkpoints/                    ->  models/checkpoints
loras/                          ->  models/loras
vae/                            ->  models/vae
controlnet/                     ->  models/controlnet
```

### VoltaML

```
MASTER                          ->  VoltaML-Pfad
checkpoints/                    ->  models/checkpoints
loras/                          ->  models/loras
vae/                            ->  models/vae
controlnet/                     ->  models/controlnet
upscalers/ (zusammengefuehrt)   ->  models/upscalers
```

---

# TEIL E: ARCHITEKTUR

## E1. Kern-Architektur aller Diffusionsmodelle

```
┌─────────────────┐
│   Checkpoint     │  = zusammengefuehrtes UNet + VAE + CLIP
└────────┬────────┘
         │ zerlegt sich in:
         v
┌──────┐  ┌─────┐  ┌──────────────┐  ┌───────────┐
│ UNet │  │ VAE │  │ Text Encoder │  │ Scheduler │
└──────┘  └─────┘  └──────────────┘  └───────────┘

Zusatzmodelle (unabhaengig):
  LoRA, ControlNet, IPAdapter, Upscaler, Erkennung, Pose, Tiefe
```

Dieselbe .safetensors-Checkpoint-Datei funktioniert identisch in
Forge, ComfyUI, Fooocus, SD.Next, InvokeAI usw.

Der Unterschied zwischen UIs liegt ausschliesslich in der Orchestrierung,
nicht im Modellformat.

## E2. Speicherersparnis durch gemeinsame Bibliothek

| Szenario | Ohne Symlinks | Mit Master-Struktur | Ersparnis |
|----------|---------------|---------------------|-----------|
| 2 UIs, 50 GB Modelle | ~100 GB | ~50 GB | 50 GB |
| 4 UIs, 200 GB Modelle | ~800 GB | ~200 GB | 600 GB |
| 6 UIs, 500 GB Modelle | ~3 TB | ~500 GB | 2,5 TB |

Symlinks kosten null zusaetzlichen Speicherplatz.

---

# TEIL F: ERKANNTE PROBLEME

## F1. Doppelte leere Verzeichnisse

Mehrere Modelltypen existieren sowohl mit Daten als auch als leere Platzhalter:

| Mit Daten | Leeres Duplikat |
|-----------|----------------|
| ClipVision/ (440,7 MB) | clip_vision/ (leer) |
| Codeformer/ (359,2 MB) | Codeformer/ (leer, Duplikat) |
| IpAdapter/ (16,1 MB) | IpAdapter/, IpAdapters15/, IpAdaptersXl/ (leere Duplikate) |
| hypernetworks/ (in ControlNet) | Hypernetwork/, hypernetworks/ (leer) |

**Empfehlung:** Leere Duplikate loeschen oder per Symlink auf den Ordner mit Daten verweisen.

## F2. Inkonsistente Benennung

Mix aus PascalCase, lowercase und UPPERCASE:
- `ClipVision` vs `clip_vision`
- `Codeformer` vs `CodeFormer`
- `IpAdapter` vs `IPAdapter` vs `ip_adapter`

StabilityMatrix handhabt das intern, aber das Dateisystem ist unuebersichtlich.

## F3. T2I-Adapter in ControlNet verschachtelt

T2I-Adapter sind als Unterordner in ControlNet/ eingebettet.
Besser waere ein eigener Top-Level-Ordner `t2i_adapter/`.

## F4. LLM-Modelle fehl am Platz

`__LLM/` (85,9 MB GGUF-Modelle) gehoert nicht in die Diffusions-Hierarchie.
Sollte in einen separaten `llm/` Ordner oder ganz raus.

## F5. Fehlende Modell-Inhalte

- `Checkpoints/WAN/` = nur 163 Bytes (Platzhalter)
- `Lora/Flux/` = leer
- `Checkpoints/SVD/` = leer

## F6. Zwei StabilityMatrix-Pfade

- `D:\Programme\stability_matrix\` (aktiv, 300,5 GB Modelle)
- `D:\Programme\StabilityMatrix\Data\` (520,5 GB)

Moeglicherweise alte + neue Installation. Pruefen ob konsolidierbar.
