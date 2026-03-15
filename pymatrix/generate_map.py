"""
AI Universe Map Generator
Erzeugt einen Graphen mit 2000-3000 Knoten über das KI/Stable-Diffusion Ökosystem.

Exportformate:
  - Neo4j  : nodes.csv + edges.csv + schema.cypher
  - Gephi  : ai_universe.gexf
  - Obsidian: obsidian/ (Markdown + Wikilinks)
  - Graphviz: ai_universe.dot

Aufruf: python generate_map.py [--format all|neo4j|gephi|obsidian|graphviz]
"""

import json
import os
import re
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import argparse
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# DATEN-DEFINITIONEN
# ─────────────────────────────────────────────────────────────────────────────

ORGANIZATIONS = [
    # Diffusion Labs / Image Gen
    ("org_stability_ai",        "Stability AI",             "Organization", "Gegründet 2019, Stable Diffusion Schöpfer"),
    ("org_black_forest_labs",   "Black Forest Labs",        "Organization", "FLUX Modell Entwickler"),
    ("org_civitai",             "CivitAI",                  "Organization", "Größte Community-Plattform für SD-Modelle"),
    ("org_huggingface",         "Hugging Face",             "Organization", "ML Model Hub und Framework Anbieter"),
    ("org_runwayml",            "RunwayML",                 "Organization", "Generative AI für Video und Bild"),
    ("org_midjourney",          "Midjourney",               "Organization", "Proprietäres Image-Generierungssystem"),
    ("org_adobe",               "Adobe",                    "Organization", "Firefly / Photoshop AI Integration"),
    ("org_openai",              "OpenAI",                   "Organization", "DALL-E, Sora, ChatGPT"),
    ("org_google",              "Google DeepMind",          "Organization", "Imagen, Gemini, VideoPoet"),
    ("org_meta",                "Meta AI",                  "Organization", "LLaMA, Emu, Movie Gen"),
    ("org_microsoft",           "Microsoft",                "Organization", "Azure AI, Designer, Copilot"),
    ("org_nvidia",              "NVIDIA",                   "Organization", "GPU Hardware, eDiff-I, Picasso"),
    ("org_amazon",              "Amazon AWS",               "Organization", "Titan Image Generator"),
    ("org_baidu",               "Baidu",                    "Organization", "ERNIE-ViLG"),
    ("org_tencent",             "Tencent",                  "Organization", "Hunyuan DiT"),
    ("org_alibaba",             "Alibaba DAMO",             "Organization", "SDXL-Turbo Beiträge"),
    ("org_bytedance",           "ByteDance",                "Organization", "MagicVideo, SDXL-Lightning"),
    ("org_deepseek",            "DeepSeek",                 "Organization", "Efficient Diffusion Research"),
    ("org_kolors_team",         "Kwai-Kolors",              "Organization", "Kolors Modell"),
    ("org_ideogram",            "Ideogram",                 "Organization", "Text-in-Image Spezialist"),
    ("org_leonardo_ai",         "Leonardo AI",              "Organization", "Fine-tuned SD Plattform"),
    ("org_playgroundai",        "Playground AI",            "Organization", "Playground v2 / v2.5"),
    ("org_segmindai",           "Segmind",                  "Organization", "SSD-1B, Würstchen"),
    ("org_ostris",              "Ostris",                   "Organization", "Flux LoRA Trainer"),
    ("org_kohya_ss",            "Kohya-ss",                 "Organization", "Kohya Training Scripts"),
    ("org_lllyasviel",          "lllyasviel",               "Organization", "ControlNet Erfinder"),
    ("org_madebyollin",         "madebyollin",              "Organization", "TAESD / ApproxVAE"),
    ("org_cerspense",           "cerspense",                "Organization", "Zeroscope Video Diffusion"),
    ("org_camenduru",           "camenduru",                "Organization", "Colab Notebooks Kurator"),
    ("org_thudm",               "THUDM",                    "Organization", "CogVideo, CogView"),
    ("org_lightricks",          "Lightricks",               "Organization", "LTX-Video Diffusion"),
    ("org_wan_team",            "Wan Video Team",           "Organization", "WAN Video T2V/I2V"),
    ("org_invoke_ai",           "Invoke AI Inc",            "Organization", "InvokeAI Framework"),
    ("org_comfyanonymous",      "comfyanonymous",           "Organization", "ComfyUI Entwickler"),
    ("org_automatic1111",       "AUTOMATIC1111",            "Organization", "SD WebUI Entwickler"),
    ("org_llava_team",          "LLaVA Team",               "Organization", "Large Language and Vision"),
    ("org_apple",               "Apple",                    "Organization", "Core ML, Stable Diffusion on-device"),
    ("org_intel",               "Intel",                    "Organization", "OpenVINO, Arc GPU Support"),
    ("org_amd",                 "AMD",                      "Organization", "ROCm GPU Compute"),
    ("org_taiyi_team",          "IDEA Research",            "Organization", "Taiyi Diffusion (Chinesisch)"),
    ("org_laion",               "LAION",                    "Organization", "Open Datasets für Training"),
    ("org_cohere",              "Cohere",                   "Organization", "Embed / Generate APIs"),
    ("org_anthropic",           "Anthropic",                "Organization", "Claude LLM Familie"),
    ("org_mosaic_ml",           "MosaicML",                 "Organization", "Wüstchen / Kandinsky Beiträge"),
    ("org_sber",                "Sber AI",                  "Organization", "Kandinsky Diffusion"),
    ("org_jina_ai",             "Jina AI",                  "Organization", "CLIP Embeddings"),
    ("org_pickapic_team",       "PickAPic Team",            "Organization", "HPS v2 Human Preference"),
    ("org_civitai_team",        "CivitAI Contributors",     "Organization", "Community Fine-Tunes"),
    ("org_stableswarm_team",    "StableSwarm Team",         "Organization", "StableSwarmUI"),
    ("org_foocus_team",         "Fooocus Team",             "Organization", "Fooocus WebUI"),
    ("org_noobai",              "NoobAI Dev",               "Organization", "NoobAI XL Modell"),
    ("org_illustrious_team",    "Illustrious Team",         "Organization", "Illustrious XL"),
    ("org_pony_diffusion",      "PonyDiffusion",            "Organization", "Pony Diffusion Modell"),
]

ARCHITECTURES = [
    ("arch_unet",           "UNet",                     "Architecture", "Klassische U-Net Diffusionsarchitektur (SD 1.x / 2.x / XL)"),
    ("arch_dit",            "DiT",                      "Architecture", "Diffusion Transformer (Scalable Diffusion)"),
    ("arch_mmdit",          "MM-DiT",                   "Architecture", "Multi-Modal DiT (SD3, Flux)"),
    ("arch_vae",            "VAE",                      "Architecture", "Variational Autoencoder (Latent Encoder/Decoder)"),
    ("arch_vqvae",          "VQ-VAE",                   "Architecture", "Vector-Quantized VAE"),
    ("arch_clip",           "CLIP",                     "Architecture", "Contrastive Language-Image Pretraining"),
    ("arch_t5",             "T5",                       "Architecture", "Text-to-Text Transfer Transformer (Encoder)"),
    ("arch_llm_encoder",    "LLM Text Encoder",         "Architecture", "Large Language Model als Text Encoder"),
    ("arch_controlnet",     "ControlNet",               "Architecture", "Conditional Control mit Zero-Convolutions"),
    ("arch_lora",           "LoRA",                     "Architecture", "Low-Rank Adaptation Feintuning"),
    ("arch_lycoris",        "LyCORIS",                  "Architecture", "Lora beYond Conventional Methods"),
    ("arch_dora",           "DoRA",                     "Architecture", "Weight-Decomposed Low-Rank Adaptation"),
    ("arch_hypernetwork",   "Hypernetwork",             "Architecture", "Metanetz das Netzgewichte modifiziert"),
    ("arch_ipadapter",      "IP-Adapter",               "Architecture", "Image Prompt Adapter via Decoupled Cross-Attention"),
    ("arch_t2i_adapter",    "T2I-Adapter",              "Architecture", "Lightweight Structural Control Adapter"),
    ("arch_svd",            "SVD (Stable Video)",       "Architecture", "Temporale Aufmerksamkeit für Video"),
    ("arch_animate_diff",   "AnimateDiff",              "Architecture", "Motion Module für Video aus SD"),
    ("arch_instruct_pix2pix","InstructPix2Pix",         "Architecture", "Instruction-based Image Editing"),
    ("arch_textual_inv",    "Textual Inversion",        "Architecture", "Embedding neuer Konzepte im CLIP-Raum"),
    ("arch_dreambooth",     "DreamBooth",               "Architecture", "Subjekt-spezifisches Feintuning"),
    ("arch_kandinsky",      "Kandinsky",                "Architecture", "CLIP-prior + UNet Diffusion"),
    ("arch_würstchen",      "Wuerstchen",               "Architecture", "Dreistufige Latent Diffusion"),
    ("arch_lcm",            "LCM",                      "Architecture", "Latent Consistency Model (schnell)"),
    ("arch_turbo",          "Turbo / Lightning",        "Architecture", "Adversarial Distillation für Speed"),
    ("arch_flow_matching",  "Flow Matching",            "Architecture", "Rektifizierte Flows (Flux Basis)"),
    ("arch_transformer_v",  "Video Transformer",        "Architecture", "Full-Attention Video Diffusion"),
    ("arch_open_clip",      "OpenCLIP",                 "Architecture", "Open-Source CLIP Implementierung"),
    ("arch_blip",           "BLIP-2",                   "Architecture", "Vision-Language Bootstrap"),
    ("arch_sam",            "SAM",                      "Architecture", "Segment Anything Model"),
    ("arch_esrgan",         "ESRGAN",                   "Architecture", "Enhanced Super-Resolution GAN"),
    ("arch_realesrgan",     "Real-ESRGAN",              "Architecture", "Real-world Super-Resolution"),
    ("arch_swinir",         "SwinIR",                   "Architecture", "Swin Transformer Image Restoration"),
    ("arch_scunet",         "SCUNet",                   "Architecture", "Swin-Conv-UNet Denoising"),
    ("arch_gfpgan",         "GFPGAN",                   "Architecture", "Generative Face Restoration GAN"),
    ("arch_codeformer",     "CodeFormer",               "Architecture", "Code-Former Face Restoration"),
    ("arch_deepdanbooru",   "DeepDanbooru",             "Architecture", "Anime Tag Klassifikator"),
    ("arch_yolo",           "YOLO",                     "Architecture", "You Only Look Once Objekterkennung"),
    ("arch_openpose",       "OpenPose",                 "Architecture", "Skelett-basierte Pose Estimation"),
    ("arch_depth_midas",    "MiDaS Depth",              "Architecture", "Monokulare Tiefenschätzung"),
    ("arch_mllm_llava",     "LLaVA",                    "Architecture", "Visual Instruction Tuning LLM"),
    ("arch_wan",            "WAN Architecture",         "Architecture", "WAN Video Diffusion Basis"),
    ("arch_ltxv",           "LTX-Video",                "Architecture", "Lightricks Video DiT"),
    ("arch_cogvideox",      "CogVideoX",                "Architecture", "Video Expert Transformer"),
    ("arch_hunyuan_video",  "Hunyuan Video",            "Architecture", "3D-Causal VAE + MLLM"),
    ("arch_hidream",        "HiDream",                  "Architecture", "Mixture-of-Experts Diffusion"),
]

BASE_MODELS = [
    # SD 1.x Familie
    ("bm_sd14",         "SD 1.4",               "BaseModel", "Erste stabile Version, 512px"),
    ("bm_sd15",         "SD 1.5",               "BaseModel", "De-facto Standard, 512px"),
    ("bm_sd15_lcm",     "SD 1.5 LCM",           "BaseModel", "LCM-distilled 1.5 für 4-8 Schritte"),
    ("bm_sd15_turbo",   "SD 1.5 Turbo",         "BaseModel", "Adversarial Distilled 1.5"),
    ("bm_sd15_hyper",   "SD 1.5 Hyper",         "BaseModel", "Hyperscale Distilled 1.5"),
    # SD 2.x Familie
    ("bm_sd20",         "SD 2.0",               "BaseModel", "OpenCLIP H/14, 512/768px"),
    ("bm_sd21",         "SD 2.1",               "BaseModel", "OpenCLIP H/14, 768px verbessert"),
    ("bm_sd21_unclip",  "SD 2.1 UnCLIP",        "BaseModel", "CLIP-Prior Variante"),
    ("bm_sdxl_base",    "SDXL 1.0 Base",        "BaseModel", "1024px Dual Text-Encoder"),
    ("bm_sdxl_refiner", "SDXL 1.0 Refiner",     "BaseModel", "High-Freq Detail Verfeinerung"),
    ("bm_sdxl_turbo",   "SDXL Turbo",           "BaseModel", "Real-time Single-Step via ADD"),
    ("bm_sdxl_lightning","SDXL Lightning",       "BaseModel", "Progressive Adversarial Distillation"),
    ("bm_sdxl_hyper",   "SDXL Hyper",           "BaseModel", "ByteDance Hyper Distillation"),
    ("bm_sdxl_lcm",     "SDXL LCM",             "BaseModel", "LCM-Distilled SDXL"),
    # Sondermodelle 1.5-Epoche
    ("bm_anything_v3",  "Anything V3",          "BaseModel", "Anime-fokussiertes SD1.5 Basis"),
    ("bm_anything_v5",  "Anything V5",          "BaseModel", "Anime SD1.5 Community Modell"),
    # Pony Familie
    ("bm_pony",         "Pony Diffusion V6 XL", "BaseModel", "SDXL-Basis, bewertet E621"),
    ("bm_pony_v7",      "Pony V7",              "BaseModel", "Verbesserte Pony Generation"),
    ("bm_noobai_xl",    "NoobAI XL",            "BaseModel", "Anime XL Community Modell"),
    ("bm_illustrious",  "Illustrious XL",       "BaseModel", "High-Res Anime XL"),
    # FLUX Familie
    ("bm_flux1_dev",    "FLUX.1 [dev]",         "BaseModel", "Flow Matching, 12B Parameter"),
    ("bm_flux1_schnell","FLUX.1 [schnell]",     "BaseModel", "4-Schritt Distilled Flux"),
    ("bm_flux1_pro",    "FLUX.1 [pro]",         "BaseModel", "API-only kommerzielle Version"),
    ("bm_flux_kontext", "FLUX Kontext",         "BaseModel", "Flux mit Kontext-Referenz"),
    ("bm_flux_krea",    "FLUX Krea",            "BaseModel", "Krea Fine-tune Flux"),
    ("bm_flux2",        "FLUX 2",               "BaseModel", "Nächste Generation Flux"),
    # PixArt Familie
    ("bm_pixart_alpha", "PixArt-α",             "BaseModel", "DiT-basiertes Text-to-Image"),
    ("bm_pixart_sigma", "PixArt-Σ",             "BaseModel", "Höhere Auflösung DiT"),
    # Hunyuan
    ("bm_hunyuan_dit",  "Hunyuan DiT",          "BaseModel", "Tencent 1.5B DiT Chinesisch"),
    ("bm_hunyuan_video","Hunyuan Video",         "BaseModel", "13B Video Diffusion Transformer"),
    # Video Modelle
    ("bm_svd_xt",       "SVD XT 1.1",           "BaseModel", "Stable Video Diffusion 25 Frames"),
    ("bm_wan_t2v",      "WAN Video T2V",        "BaseModel", "Text-to-Video 14B"),
    ("bm_wan_i2v",      "WAN Video I2V",        "BaseModel", "Image-to-Video 14B"),
    ("bm_cogvideox_2b", "CogVideoX 2B",         "BaseModel", "Video Expert Transformer klein"),
    ("bm_cogvideox_5b", "CogVideoX 5B",         "BaseModel", "Video Expert Transformer groß"),
    ("bm_ltxv",         "LTX-Video",            "BaseModel", "Lightricks Real-time Video"),
    ("bm_mochi",        "Mochi 1",              "BaseModel", "Genmo Video Modell"),
    # Weitere Image Modelle
    ("bm_sd3",          "SD 3.0",               "BaseModel", "MM-DiT, Triple Text Encoder"),
    ("bm_sd35_medium",  "SD 3.5 Medium",        "BaseModel", "2B MM-DiT"),
    ("bm_sd35_large",   "SD 3.5 Large",         "BaseModel", "8B MM-DiT"),
    ("bm_auraflow",     "AuraFlow",             "BaseModel", "Open Flow Matching Modell"),
    ("bm_kolors",       "Kolors",               "BaseModel", "Chinesisch-Englisch SDXL Variante"),
    ("bm_lumina",       "Lumina",               "BaseModel", "Next-DiT für Hochauflösung"),
    ("bm_playground_v2","Playground v2",        "BaseModel", "ästhetisches SDXL Derivat"),
    ("bm_playground_v25","Playground v2.5",     "BaseModel", "Verbessert mit EDM-Formulierung"),
    ("bm_hidream_i1",   "HiDream I1",           "BaseModel", "MoE Diffusion 17B"),
    ("bm_cosmos",       "NVIDIA Cosmos",        "BaseModel", "World Foundation Model Video"),
    ("bm_kandinsky_21", "Kandinsky 2.1",        "BaseModel", "CLIP-Prior + Diffusion"),
    ("bm_kandinsky_22", "Kandinsky 2.2",        "BaseModel", "CLIP Vision Encoder verbessert"),
    ("bm_kandinsky_3",  "Kandinsky 3",          "BaseModel", "UNet + T5 Text Encoder"),
    ("bm_deepfloyd_if", "DeepFloyd IF",         "BaseModel", "Pixel-Space Cascaded Diffusion"),
    ("bm_würstchen_v2", "Würstchen v2",         "BaseModel", "Dreistufige komprimierte Diffusion"),
    ("bm_würstchen_v3", "Würstchen v3",         "BaseModel", "SANA-ähnliche Architektur"),
    ("bm_animatediff",  "AnimateDiff v3",       "BaseModel", "Motion Module für SD1.5"),
    ("bm_animatediff_xl","AnimateDiff XL",      "BaseModel", "Motion Module für SDXL"),
]

MODEL_TYPES = [
    ("mt_checkpoint",   "Checkpoint",           "ModelType", "Vollständiges Diffusionsmodell (.safetensors/.ckpt)"),
    ("mt_lora",         "LoRA",                 "ModelType", "Low-Rank Adaptation für Feintuning"),
    ("mt_lycoris",      "LyCORIS",              "ModelType", "Erweiterte LoRA Methoden (LoHa, LoKr, etc.)"),
    ("mt_dora",         "DoRA",                 "ModelType", "Weight-Decomposed LoRA"),
    ("mt_loha",         "LoHa",                 "ModelType", "Low-Rank Hadamard Product"),
    ("mt_lokr",         "LoKr",                 "ModelType", "Low-Rank Kronecker Product"),
    ("mt_ia3",          "IA3",                  "ModelType", "Inhibit and Amplify Adapter"),
    ("mt_vae",          "VAE",                  "ModelType", "Variational Autoencoder"),
    ("mt_vae_approx",   "VAE Approx",           "ModelType", "Schnelle VAE Approximation für Preview"),
    ("mt_embedding",    "Embedding",            "ModelType", "Textual Inversion Embedding"),
    ("mt_hypernetwork", "Hypernetwork",         "ModelType", "Meta-Netzwerk für Style-Transfer"),
    ("mt_controlnet",   "ControlNet",           "ModelType", "Strukturkontroll-Netzwerk"),
    ("mt_controlnet_xl","ControlNet XL",        "ModelType", "ControlNet für SDXL"),
    ("mt_t2i_adapter",  "T2I-Adapter",          "ModelType", "Leichtgewichtiger Konditionierungsadapter"),
    ("mt_ipadapter",    "IP-Adapter",           "ModelType", "Bildprompt-Adapter"),
    ("mt_ipadapter_faceid","IP-Adapter FaceID", "ModelType", "Gesichts-ID IP-Adapter"),
    ("mt_upscaler",     "Upscaler",             "ModelType", "Super-Resolution Modell"),
    ("mt_face_restore", "Face Restore",         "ModelType", "Gesichtswiederherstellung"),
    ("mt_detection",    "Detection",            "ModelType", "Objekterkennung / YOLO"),
    ("mt_segmentation", "Segmentation",         "ModelType", "Bildsegmentierung (SAM)"),
    ("mt_depth",        "Depth Estimation",     "ModelType", "Tiefenschätzung"),
    ("mt_pose",         "Pose Estimation",      "ModelType", "Skelett-Pose Erkennung"),
    ("mt_caption",      "Captioning",           "ModelType", "Automatische Bildbeschreibung"),
    ("mt_clip_model",   "CLIP Model",           "ModelType", "Image-Text Embedding Modell"),
    ("mt_text_encoder", "Text Encoder",         "ModelType", "Textverarbeitungs-Encoder"),
    ("mt_unet",         "UNet Komponent",       "ModelType", "UNet als separate Komponente"),
    ("mt_diffuser",     "Diffusers Model",      "ModelType", "HuggingFace Diffusers Format"),
    ("mt_motion_module","Motion Module",        "ModelType", "Temporale Attention für Video"),
    ("mt_style_model",  "Style Model",          "ModelType", "FLUX Redux Style Konditionierung"),
    ("mt_gligen",       "GLIGEN",               "ModelType", "Grounded Language-Image Generation"),
    ("mt_workflow",     "Workflow",             "ModelType", "ComfyUI / Swarm Workflow-Datei"),
    ("mt_wildcard",     "Wildcard",             "ModelType", "Zufalls-Prompt-Textdatei"),
    ("mt_lut",          "LUT",                  "ModelType", "Look-Up Table für Farbkorrektur"),
]

WEBUIS = [
    ("ui_a1111",        "AUTOMATIC1111",            "WebUI", "De-facto Standard WebUI"),
    ("ui_forge",        "SD WebUI Forge",           "WebUI", "Forge Fork mit Speicheroptimierung"),
    ("ui_reforge",      "SD WebUI reForge",         "WebUI", "reForge Community Fork"),
    ("ui_amdgpu_forge", "AMDGPU Forge",             "WebUI", "ROCm-optimierter Forge Fork"),
    ("ui_directml",     "A1111 DirectML",           "WebUI", "DirectML Backend für Windows"),
    ("ui_sdnext",       "SD.Next",                  "WebUI", "Vladimir's modularer Fork"),
    ("ui_webui_ux",     "SD WebUI-UX",              "WebUI", "UX-verbesserte WebUI"),
    ("ui_comfyui",      "ComfyUI",                  "WebUI", "Node-basierte Diffusion Pipeline"),
    ("ui_fooocus",      "Fooocus",                  "WebUI", "Einfache Midjourney-ähnliche UI"),
    ("ui_fooocus_mre",  "Fooocus MRE",              "WebUI", "Fooocus mit erweiterten Features"),
    ("ui_fooocus_cn",   "Fooocus ControlNet SDXL",  "WebUI", "Fooocus mit ControlNet"),
    ("ui_ruined_fooocus","Ruined Fooocus",           "WebUI", "Community Fooocus Fork"),
    ("ui_fooocus_1up",  "Fooocus 1-Up Edition",     "WebUI", "mashb1t's Fooocus Erweiterung"),
    ("ui_simplesdxl",   "SimpleSDXL",               "WebUI", "Minimales SDXL Interface"),
    ("ui_swarmui",      "StableSwarmUI",             "WebUI", "Cluster-fähiges WebUI"),
    ("ui_invokeai",     "InvokeAI",                 "WebUI", "Model Registry UI"),
    ("ui_sdfx",         "SDFX",                     "WebUI", "Workflow-orientiertes Interface"),
    ("ui_voltaml",      "VoltaML",                  "WebUI", "Pipeline-basierte UI"),
    ("ui_kohya",        "Kohya GUI",                "WebUI", "Training GUI"),
    ("ui_onetrainer",   "OneTrainer",               "WebUI", "Universelles Training Tool"),
    ("ui_fluxgym",      "FluxGym",                  "WebUI", "Flux LoRA Training"),
    ("ui_cogstudio",    "CogStudio",                "WebUI", "CogVideo Training/Inference"),
    ("ui_stability_matrix","StabilityMatrix",       "WebUI", "Package Manager für alle UIs"),
    ("ui_pinokio",      "Pinokio",                  "WebUI", "Browser-basierter AI App Launcher"),
    ("ui_drawthings",   "Draw Things",              "WebUI", "macOS/iOS App"),
    ("ui_diffusionbee", "DiffusionBee",             "WebUI", "macOS Desktop App"),
    ("ui_mochi_diffusion","Mochi Diffusion",        "WebUI", "macOS Native App"),
    ("ui_invokeai_v4",  "InvokeAI v4",              "WebUI", "Überarbeitetes Canvas Interface"),
    ("ui_artbot",       "ArtBot",                   "WebUI", "Web-basierter Client für Horde"),
    ("ui_openart",      "OpenArt AI",               "WebUI", "Online Plattform"),
]

TRAINING_FRAMEWORKS = [
    ("tf_kohya_scripts", "Kohya-ss Scripts",    "TrainingFramework", "Python Scripts für LoRA/DreamBooth"),
    ("tf_onetrainer",   "OneTrainer",           "TrainingFramework", "Universelles Training mit GUI"),
    ("tf_fluxgym",      "FluxGym",              "TrainingFramework", "Einfaches Flux LoRA Training"),
    ("tf_dreambooth_ext","DreamBooth Extension","TrainingFramework", "A1111 Extension für DreamBooth"),
    ("tf_everyDream",   "EveryDream 2",         "TrainingFramework", "Checkpoint Fine-tuning"),
    ("tf_simpletrain",  "SimpleTuner",          "TrainingFramework", "Modernes SDXL/Flux Training"),
    ("tf_x_flux",       "x-flux",               "TrainingFramework", "Black Forest Labs Flux Training"),
    ("tf_ai_toolkit",   "AI Toolkit",           "TrainingFramework", "Ostris Flux Training Toolkit"),
    ("tf_prodigy",      "Prodigy Optimizer",    "TrainingFramework", "Adaptiver Lernraten-Optimizer"),
    ("tf_lycoris_lib",  "LyCORIS Library",      "TrainingFramework", "Python Lib für LyCORIS Methoden"),
    ("tf_bitsandbytes", "BitsAndBytes",         "TrainingFramework", "8-bit/4-bit Quantisierung"),
    ("tf_xformers",     "xFormers",             "TrainingFramework", "Memory-effiziente Attention"),
    ("tf_deepspeed",    "DeepSpeed",            "TrainingFramework", "Distributed Training"),
    ("tf_accelerate",   "Hugging Face Accelerate","TrainingFramework","Multi-GPU Abstraktionslayer"),
    ("tf_diffusers_lib","Diffusers Library",    "TrainingFramework", "HF Diffusers Python Library"),
    ("tf_transformers", "Transformers Library", "TrainingFramework", "HF Transformers Python Library"),
]

DATASETS = [
    ("ds_laion_5b",     "LAION-5B",             "Dataset", "5 Milliarden Image-Text Paare"),
    ("ds_laion_aesthetics","LAION Aesthetics",  "Dataset", "Ästhetisch gefilterte LAION Subset"),
    ("ds_coyo_700m",    "COYO-700M",            "Dataset", "700M korreliertes Image-Text"),
    ("ds_cc3m",         "CC3M",                 "Dataset", "Conceptual Captions 3M"),
    ("ds_cc12m",        "CC12M",                "Dataset", "Conceptual Captions 12M"),
    ("ds_laion_art",    "LAION Art",            "Dataset", "Kunstfokussiertes Dataset"),
    ("ds_danbooru",     "Danbooru",             "Dataset", "Anime Illustrations mit Tags"),
    ("ds_e621",         "e621",                 "Dataset", "Furry/Anime Content mit Tags"),
    ("ds_civitai_data", "CivitAI Community Data","Dataset","Community-generierte Bilder"),
    ("ds_jdb",          "JourneyDB",            "Dataset", "Midjourney-generierte Bilder"),
    ("ds_diffusiondb",  "DiffusionDB",          "Dataset", "SD-generierte Bilder + Prompts"),
    ("ds_pokemon_blip", "Pokemon BLIP Captions","Dataset", "Pokemon Dataset mit BLIP Captions"),
    ("ds_celeba_hq",    "CelebA-HQ",            "Dataset", "High-Quality Gesichts Dataset"),
    ("ds_ffhq",         "FFHQ",                 "Dataset", "Flickr Faces High Quality"),
    ("ds_openimages",   "Open Images V7",       "Dataset", "Google Open Images Dataset"),
    ("ds_imagenet",     "ImageNet 21K",         "Dataset", "Classification Pre-training"),
    ("ds_wikiart",      "WikiArt",              "Dataset", "Kunstwerke nach Stil/Künstler"),
    ("ds_sa1b",         "SA-1B",                "Dataset", "SAM 1 Milliarde Masken"),
    ("ds_logo_2k",      "Logo-2K+",             "Dataset", "Logo Recognition Dataset"),
    ("ds_laion_en",     "LAION en",             "Dataset", "Englischsprachiges LAION"),
    ("ds_webvid10m",    "WebVid-10M",           "Dataset", "10M Video-Text Paare"),
    ("ds_hdvila",       "HD-VILA-100M",         "Dataset", "100M HD Video Clips"),
    ("ds_panda70m",     "Panda-70M",            "Dataset", "70M semantische Video Clips"),
    ("ds_internvid",    "InternVid-10M",        "Dataset", "10M Video mit Captions"),
]

CONTROLNET_MODELS = [
    ("cn_canny",        "ControlNet Canny",         "ControlNetModel", "Kantendetektion Konditionierung"),
    ("cn_depth",        "ControlNet Depth",         "ControlNetModel", "Tiefenkarte Konditionierung"),
    ("cn_openpose",     "ControlNet OpenPose",      "ControlNetModel", "Körperpose Konditionierung"),
    ("cn_mlsd",         "ControlNet MLSD",          "ControlNetModel", "Gerade Linien Erkennung"),
    ("cn_hed",          "ControlNet HED",           "ControlNetModel", "Soft-Edge Detektion"),
    ("cn_scribble",     "ControlNet Scribble",      "ControlNetModel", "Skizze/Kritzelkonditionierung"),
    ("cn_segmentation", "ControlNet Segmentation",  "ControlNetModel", "Semantische Segmentation"),
    ("cn_normal_map",   "ControlNet Normal Map",    "ControlNetModel", "Normalvektorkarten"),
    ("cn_inpainting",   "ControlNet Inpainting",    "ControlNetModel", "Inpainting Spezialmodell"),
    ("cn_tile",         "ControlNet Tile",          "ControlNetModel", "Kachel-Textur Konditionierung"),
    ("cn_shuffle",      "ControlNet Shuffle",       "ControlNetModel", "Zufällige Style Permutation"),
    ("cn_ip2p",         "ControlNet InstructP2P",   "ControlNetModel", "Instruktionsbasierte Bearbeitung"),
    ("cn_lineart",      "ControlNet Lineart",       "ControlNetModel", "Linienzeichnung Konditionierung"),
    ("cn_lineart_anime","ControlNet Lineart Anime", "ControlNetModel", "Anime Lineart Konditionierung"),
    ("cn_animal_pose",  "ControlNet Animal Pose",   "ControlNetModel", "Tier-Pose Erkennung"),
    ("cn_face_id",      "ControlNet FaceID",        "ControlNetModel", "Gesichtsidentität Konditionierung"),
    ("cn_ipadapter_xl", "ControlNet IPA XL",        "ControlNetModel", "IP-Adapter XL Variante"),
    ("cn_reference",    "ControlNet Reference",     "ControlNetModel", "Stil-Referenz ohne Modell"),
    ("cn_denspose",     "ControlNet DensePose",     "ControlNetModel", "Dichte Körper-UV-Karte"),
    ("cn_canny_xl",     "ControlNet Canny XL",      "ControlNetModel", "Canny für SDXL"),
    ("cn_depth_xl",     "ControlNet Depth XL",      "ControlNetModel", "Depth für SDXL"),
    ("cn_openpose_xl",  "ControlNet OpenPose XL",   "ControlNetModel", "Pose für SDXL"),
    ("cn_blur",         "ControlNet Blur",          "ControlNetModel", "Weichzeichner Konditionierung"),
    ("cn_recolor",      "ControlNet Recolor",       "ControlNetModel", "Einfärbung Konditionierung"),
    ("cn_mediapipe_face","ControlNet MediaPipe Face","ControlNetModel","Gesichts-Mesh Konditionierung"),
    ("cn_flux_canny",   "Flux ControlNet Canny",    "ControlNetModel", "Canny für Flux"),
    ("cn_flux_depth",   "Flux ControlNet Depth",    "ControlNetModel", "Depth für Flux"),
    ("cn_union",        "ControlNet Union",         "ControlNetModel", "Einheitliches Multi-Control Modell"),
]

UPSCALERS = [
    ("up_esrgan_4x",    "ESRGAN 4x",            "Upscaler", "4x Super-Resolution"),
    ("up_real_esrgan",  "Real-ESRGAN 4x+",      "Upscaler", "Real-World 4x Upscaling"),
    ("up_real_esrgan_anime","Real-ESRGAN Anime 6B","Upscaler","Anime-optimiertes Upscaling"),
    ("up_ultrasharp",   "4x-UltraSharp",        "Upscaler", "Schärfungs-Upscaler"),
    ("up_nmkd_siax",    "NMKD Siax",            "Upscaler", "Allzweck ESRGAN"),
    ("up_swinir",       "SwinIR 4x",            "Upscaler", "Swin Transformer SR"),
    ("up_scunet",       "SCUNet",               "Upscaler", "Rauschreduktion + SR"),
    ("up_remacri",      "Remacri",              "Upscaler", "4x Soft-Upscaler"),
    ("up_foolhardy",    "Foolhardy Remacri",    "Upscaler", "Verbesserte Remacri Version"),
    ("up_lollypop",     "4x Lollypop",         "Upscaler", "Weiches allgemeines Upscaling"),
    ("up_4x_hfa2k_ludvae","4x-HFA2k-ludvae",   "Upscaler", "Anime Upscaler"),
    ("up_sudo_shuffle", "SudoShuffle 2x",       "Upscaler", "Halbe Auflösung Upscaler"),
    ("up_dat",          "DAT",                  "Upscaler", "Dual Aggregation Transformer SR"),
    ("up_hat",          "HAT",                  "Upscaler", "Hybrid Attention Transformer SR"),
    ("up_tiled_diffusion","Tiled Diffusion",    "Upscaler", "SD-basiertes Upscaling"),
    ("up_ultimate_sd",  "Ultimate SD Upscale",  "Upscaler", "A1111 Extension Upscaler"),
]

POPULAR_CHECKPOINTS = [
    # SD 1.5 Checkpoints
    ("ckpt_dreamshaper8",   "DreamShaper 8",        "Checkpoint", "Vielseitiger SD1.5 Champion"),
    ("ckpt_realistic_vision","Realistic Vision 6",  "Checkpoint", "Fotorealistisch SD1.5"),
    ("ckpt_deliberate_v6",  "Deliberate v6",        "Checkpoint", "Allzweck SD1.5 Modell"),
    ("ckpt_epicphotogasm",  "epiCPhotoGasm",        "Checkpoint", "Fotografischer Realismus"),
    ("ckpt_chilloutmix",    "ChilloutMix",          "Checkpoint", "Asiatisch-realistische Figuren"),
    ("ckpt_aamxl_ultimate", "AbsoluteReality",      "Checkpoint", "Sehr realistisches SD1.5"),
    ("ckpt_revanimated",    "ReV Animated",         "Checkpoint", "Anime+Cartoon SD1.5"),
    ("ckpt_openjourney",    "OpenJourney v4",       "Checkpoint", "Midjourney-Stil SD1.5"),
    ("ckpt_analog_diffusion","Analog Diffusion",    "Checkpoint", "Analogfotografie-Stil"),
    ("ckpt_portrait_relax", "Portrait+ Style",      "Checkpoint", "Porträt-spezialisiert"),
    ("ckpt_hassanblend",    "HassanBlend 1.5",      "Checkpoint", "Blend verschiedener Stile"),
    ("ckpt_elldreth_sd",    "Elldreth Merged",      "Checkpoint", "Vielseitiger Merge"),
    ("ckpt_f222",           "f222",                 "Checkpoint", "Älterer Realistik-Favorit"),
    ("ckpt_classicanim",    "Classic Anime Diffusion","Checkpoint","Classic Anime Stil"),
    ("ckpt_meina_v11",      "MeinaMix V11",         "Checkpoint", "Anime/Illustration Mix"),
    # SDXL Checkpoints
    ("ckpt_juggernaut_xl",  "Juggernaut XL v9",     "Checkpoint", "Top Realistik SDXL"),
    ("ckpt_dreamshaper_xl", "DreamShaper XL 1.0",   "Checkpoint", "Vielseitig SDXL"),
    ("ckpt_realvis_xl",     "RealVisXL V4",         "Checkpoint", "Fotorealistisch SDXL"),
    ("ckpt_nightvision_xl", "NightVisionXL",        "Checkpoint", "Dramatisches Licht SDXL"),
    ("ckpt_epicrealism_xl", "EpicRealism XL",       "Checkpoint", "Ultra-realistisch SDXL"),
    ("ckpt_crystal_clear",  "CrystalClear XL",      "Checkpoint", "Klares detailliertes SDXL"),
    ("ckpt_animagine_xl3",  "Animagine XL 3.1",     "Checkpoint", "Anime SDXL Standard"),
    ("ckpt_kohaku_xl",      "Kohaku XL",            "Checkpoint", "Japanischer Anime Stil"),
    ("ckpt_counterfeit_xl", "CounterfeitXL",        "Checkpoint", "Anime Illustration XL"),
    ("ckpt_hassakuxl",      "HassaKuXL",            "Checkpoint", "Anime XL Community"),
    # Pony-basiert
    ("ckpt_pdxl",           "Pony DiffusionXL",     "Checkpoint", "Basis Pony Checkpoint"),
    ("ckpt_autismmix_pony", "AutismMix SDXL",       "Checkpoint", "Anime Pony Derivat"),
    ("ckpt_fluffydream",    "FluffyDream Pony",     "Checkpoint", "Weicher Anime Pony-Stil"),
    # Flux-basiert
    ("ckpt_flux_realism",   "Flux Realism LoRA",    "Checkpoint", "Realistischer Flux Fine-tune"),
    ("ckpt_flux_anime",     "Flux Anime",           "Checkpoint", "Anime-Stil Flux Modell"),
    ("ckpt_flux_portrait",  "Flux Portrait Master", "Checkpoint", "Porträt Flux Spezialisierung"),
    # SD3-basiert
    ("ckpt_sd3_medium",     "SD3 Medium Community", "Checkpoint", "Community SD3 Fine-tune"),
]

LORA_STYLES = [
    # Künstlerstil LoRAs
    ("lora_greg_rutkowski",     "Greg Rutkowski Style",     "LoRAModel", "Fantasy-Illustrationsweise"),
    ("lora_makoto_shinkai",     "Makoto Shinkai Style",     "LoRAModel", "Anime Filmstil"),
    ("lora_studio_ghibli",      "Studio Ghibli Style",      "LoRAModel", "Ghibli Animation Ästhetik"),
    ("lora_van_gogh",           "Van Gogh Style",           "LoRAModel", "Post-Impressionismus"),
    ("lora_watercolor",         "Watercolor Style",         "LoRAModel", "Aquarellmalerei"),
    ("lora_pixel_art",          "Pixel Art Style",          "LoRAModel", "8-bit/16-bit Pixel Art"),
    ("lora_line_art",           "Line Art Style",           "LoRAModel", "Klare Linienzeichnungen"),
    ("lora_oilpainting",        "Oil Painting Style",       "LoRAModel", "Ölgemälde Textur"),
    ("lora_pencil_sketch",      "Pencil Sketch",            "LoRAModel", "Bleistiftskizze"),
    ("lora_comic_book",         "Comic Book Style",         "LoRAModel", "Amerikanischer Comic-Stil"),
    ("lora_cyberpunk",          "Cyberpunk Style",          "LoRAModel", "Cyberpunk Ästhetik"),
    ("lora_steampunk",          "Steampunk Style",          "LoRAModel", "Viktorianisch-technologisch"),
    ("lora_lowpoly",            "Low Poly Style",           "LoRAModel", "Dreieck-Polygon Ästhetik"),
    ("lora_flat_design",        "Flat Design Style",        "LoRAModel", "Minimaler 2D Stil"),
    ("lora_impressionism",      "Impressionism Style",      "LoRAModel", "Impressionistische Malerei"),
    ("lora_photorealism",       "Photorealism Boost",       "LoRAModel", "Fotografische Detailschärfe"),
    ("lora_hdr",                "HDR Photography",          "LoRAModel", "High Dynamic Range Look"),
    ("lora_cinematic",          "Cinematic Look",           "LoRAModel", "Filmische Belichtung/Farben"),
    ("lora_35mm_film",          "35mm Film Grain",          "LoRAModel", "Analog Film Körnung"),
    ("lora_neon_lights",        "Neon Lights Style",        "LoRAModel", "Neon-Beleuchtungseffekte"),
    # Charakter/Konzept LoRAs
    ("lora_detail_tweaker",     "Add Detail XL",            "LoRAModel", "Detailschärfung Slider"),
    ("lora_more_art",           "More Art Style",           "LoRAModel", "Künstlerische Verbesserung"),
    ("lora_bad_anatomy",        "Negative Anatomy Fix",     "LoRAModel", "Anatomie-Korrektur Negativ"),
    ("lora_face_fix",           "FaceDetailer Fix",         "LoRAModel", "Gesichts-Detailverbesserung"),
    ("lora_hands_fix",          "Better Hands",             "LoRAModel", "Verbessertes Händerendering"),
    ("lora_perfect_eye",        "Perfect Eyes",             "LoRAModel", "Augendarstellungsverbesserung"),
    # NSFW-adjacent (generisch, keine spezifischen Namen)
    ("lora_clothing_detail",    "Clothing Detail",          "LoRAModel", "Textur-Detail für Kleidung"),
    ("lora_skin_texture",       "Skin Texture Enhance",     "LoRAModel", "Hautdetail-Verbesserung"),
    # Flux LoRAs
    ("lora_flux_realism",       "Flux Hyper Realism",       "LoRAModel", "Maximale Realistik für Flux"),
    ("lora_flux_lineart",       "Flux Line Art",            "LoRAModel", "Linienzeichnung mit Flux"),
    ("lora_flux_anime_xl",      "Flux Anime XL",            "LoRAModel", "Anime-Stil für Flux"),
]

EMBEDDINGS = [
    ("emb_easyneg",         "EasyNeg",              "Embedding", "Universelles Negativ-Embedding"),
    ("emb_badprompt",       "badprompt",            "Embedding", "Qualitätsverbesserungs-Negativ"),
    ("emb_bad_anatomy",     "bad_anatomy",          "Embedding", "Anatomie-Korrektiv Negativ"),
    ("emb_bad_hands",       "bad_hands",            "Embedding", "Hände-Korrektiv Negativ"),
    ("emb_ng_deepneg",      "ng_deepneg_v1",        "Embedding", "Deep Negatives v1"),
    ("emb_badquality",      "lowres_fix",           "Embedding", "Niedrige Auflösung Korrektiv"),
    ("emb_style_photo",     "portrait_style",       "Embedding", "Porträt-Stil Positiv"),
    ("emb_epicphotorealism","epicphotorealism",     "Embedding", "Ultra-Realistik Boost"),
    ("emb_easylora",        "easyLora",             "Embedding", "LoRA-like Embedding Konzept"),
    ("emb_detail_slider",   "detail_slider_v4",     "Embedding", "Detailgrad-Kontrolle"),
]

SAMPLERS = [
    ("sampler_euler",       "Euler",                "Sampler", "Einfachster Diffusions-Sampler"),
    ("sampler_euler_a",     "Euler Ancestral",      "Sampler", "Stochastischer Euler"),
    ("sampler_dpmpp_2m",    "DPM++ 2M",             "Sampler", "Schneller High-Quality Sampler"),
    ("sampler_dpmpp_sde",   "DPM++ SDE",            "Sampler", "Stochastic DPM++ Variant"),
    ("sampler_dpmpp_2s_a",  "DPM++ 2S Ancestral",   "Sampler", "2-Schritte Ancestral DPM++"),
    ("sampler_heun",        "Heun",                 "Sampler", "Runge-Kutta 2. Ordnung"),
    ("sampler_lms",         "LMS",                  "Sampler", "Linear Multi-Step"),
    ("sampler_plms",        "PLMS",                 "Sampler", "Pseudo Linear Multi-Step"),
    ("sampler_ddim",        "DDIM",                 "Sampler", "Denoising Diffusion Implicit"),
    ("sampler_ddpm",        "DDPM",                 "Sampler", "Denoising Diffusion Probabilistic"),
    ("sampler_lcm",         "LCM Sampler",          "Sampler", "Latent Consistency Sampler"),
    ("sampler_tcd",         "TCD Sampler",          "Sampler", "Trajectory Consistency Distillation"),
    ("sampler_restart",     "Restart",              "Sampler", "Restart-Sampling Methode"),
    ("sampler_unipc",       "UniPC",                "Sampler", "Unified Predictor-Corrector"),
    ("sampler_deis",        "DEIS",                 "Sampler", "Diffusion Exponential Integrator"),
    ("sampler_ode_solver",  "ODE Solver",           "Sampler", "Gewöhnlicher Differentialgleichungslöser"),
]

SCHEDULERS = [
    ("sched_karras",        "Karras",               "Scheduler", "Karras Noise Schedule"),
    ("sched_exponential",   "Exponential",          "Scheduler", "Exponentieller Noise Schedule"),
    ("sched_sgm_uniform",   "SGM Uniform",          "Scheduler", "Stochastic Gradient Match"),
    ("sched_simple",        "Simple",               "Scheduler", "Einfacher linearer Schedule"),
    ("sched_ddim_uniform",  "DDIM Uniform",         "Scheduler", "DDIM Uniform Timesteps"),
    ("sched_beta",          "Beta",                 "Scheduler", "Beta Noise Schedule"),
]

EXTENSIONS_A1111 = [
    ("ext_controlnet",      "ControlNet Extension",     "Extension", "Haupt-ControlNet Integration"),
    ("ext_adetailer",       "ADetailer",                "Extension", "Automatischer Detailverbesserter"),
    ("ext_ultimate_upscale","Ultimate SD Upscale",      "Extension", "Kachel-basiertes Upscaling"),
    ("ext_tiled_diffusion", "Tiled Diffusion",          "Extension", "Speicher-effizientes Tiling"),
    ("ext_regional_prompter","Regional Prompter",       "Extension", "Regionen-basiertes Prompting"),
    ("ext_promptall",       "Prompt All In One",        "Extension", "Multilinguale Prompt Übersetzung"),
    ("ext_wildcards",       "Wildcards",                "Extension", "Zufalls-Prompt Erweiterung"),
    ("ext_wd14_tagger",     "WD14 Tagger",              "Extension", "Automatisches Bild-Tagging"),
    ("ext_svg_prompt",      "StableSR",                 "Extension", "Stable Diffusion SR Extension"),
    ("ext_face_editor",     "Face Editor",              "Extension", "Gesichts-Bearbeitungs-Extension"),
    ("ext_batch_prompt",    "Batch Prompt",             "Extension", "Stapel-Prompt-Verarbeitung"),
    ("ext_deforum",         "Deforum Animation",        "Extension", "Video-Animation Extension"),
    ("ext_video_loopback",  "Video Loopback",           "Extension", "Video-Iterations-Extension"),
    ("ext_lobe",            "Lobe Theme",               "Extension", "Dunkles Theme"),
    ("ext_dreambooth",      "DreamBooth Extension",     "Extension", "DreamBooth Training in A1111"),
    ("ext_multidiffusion",  "MultiDiffusion",           "Extension", "Panorama und Tiling"),
    ("ext_roop",            "ReActor Face Swap",        "Extension", "Gesichtstausch-Extension"),
    ("ext_depth_anything",  "Depth Anything",           "Extension", "Tiefenkarten-Generator"),
    ("ext_openpose_ed",     "OpenPose Editor",          "Extension", "Pose-Bearbeitungs-Extension"),
    ("ext_infinite_zoom",   "Infinite Zoom",            "Extension", "Zoom-Animations-Extension"),
    ("ext_lycoris_ext",     "LyCORIS Extension",        "Extension", "LyCORIS Training Extension"),
]

COMFYUI_NODES = [
    ("node_ksampler",       "KSampler",             "ComfyNode", "Kern-Sampling Knoten"),
    ("node_load_ckpt",      "Load Checkpoint",      "ComfyNode", "Modell laden Knoten"),
    ("node_clip_encode",    "CLIP Text Encode",     "ComfyNode", "Prompt Encoding"),
    ("node_vae_decode",     "VAE Decode",           "ComfyNode", "Latent zu Bild Dekodierung"),
    ("node_vae_encode",     "VAE Encode",           "ComfyNode", "Bild zu Latent Kodierung"),
    ("node_empty_latent",   "Empty Latent Image",   "ComfyNode", "Latent-Initialisierung"),
    ("node_controlnet_ap",  "Apply ControlNet",     "ComfyNode", "ControlNet Anwendungsknoten"),
    ("node_ipadapter",      "IPAdapter Apply",      "ComfyNode", "IP-Adapter Knoten"),
    ("node_lora_loader",    "Load LoRA",            "ComfyNode", "LoRA Lade-Knoten"),
    ("node_upscale",        "Upscale Image",        "ComfyNode", "Bild-Upscaling Knoten"),
    ("node_image_save",     "Save Image",           "ComfyNode", "Bild-Speicher-Knoten"),
    ("node_image_preview",  "Preview Image",        "ComfyNode", "Vorschau-Knoten"),
    ("node_primitive",      "Primitive",            "ComfyNode", "Wert-Eingabe Knoten"),
    ("node_efficiency",     "Efficient Nodes",      "ComfyNode", "Efficiency Pack Knoten"),
    ("node_impact_pack",    "Impact Pack",          "ComfyNode", "Face Detailer etc."),
    ("node_was_node_suite", "WAS Node Suite",       "ComfyNode", "Utility-Node-Sammlung"),
    ("node_rgthree",        "rgthree Nodes",        "ComfyNode", "Power Node Suite"),
    ("node_ltxvideo",       "LTXVideo Nodes",       "ComfyNode", "LTX-Video Spezial-Nodes"),
    ("node_animatediff",    "AnimateDiff Nodes",    "ComfyNode", "AnimateDiff Node Pack"),
    ("node_comfyroll",      "ComfyRoll",            "ComfyNode", "Erweiterte Utility Nodes"),
    ("node_florence2",      "Florence2",            "ComfyNode", "Florence2 Vision Nodes"),
    ("node_pulid",          "PuLID Nodes",          "ComfyNode", "PuLID ID Consistency"),
]

# ─── Erweiterte Checkpoint-Datenbank ─────────────────────────────────────────
EXTENDED_CHECKPOINTS_SD15 = [
    # Top CivitAI SD1.5 Modelle
    ("ckpt_beautifulrealmix",   "Beautiful Real Mix",       "Checkpoint", "Realismus+Anime Blend SD1.5"),
    ("ckpt_cyberrealistic",     "CyberRealistic",           "Checkpoint", "Cyberpunk-Realismus SD1.5"),
    ("ckpt_bb95_sd15",          "BB95 Furry Mix",           "Checkpoint", "Furry/Anthro SD1.5"),
    ("ckpt_ghostmix",           "GhostMix",                 "Checkpoint", "Anime+Realismus Hybrid"),
    ("ckpt_dreamlike_anime",    "Dreamlike Anime",          "Checkpoint", "Dreamlike-Anime Stil"),
    ("ckpt_dreamlike_photo",    "Dreamlike Photoreal 2",    "Checkpoint", "Fotorealistisch Dreamlike"),
    ("ckpt_pastel_mix",         "Pastel Mix",               "Checkpoint", "Weicher Pastell Anime Stil"),
    ("ckpt_darkink",            "Dark Ink Illustration",    "Checkpoint", "Tinte+Skizze Stil"),
    ("ckpt_toonyou",            "ToonYou",                  "Checkpoint", "Cartoon Toon Stil"),
    ("ckpt_cartoon_mix",        "CartoonMix",               "Checkpoint", "Amerikanischer Cartoon"),
    ("ckpt_aniverse",           "Aniverse",                 "Checkpoint", "Anime Universe Stil"),
    ("ckpt_counterfeit_v30",    "Counterfeit V3.0",         "Checkpoint", "Anime Illustration"),
    ("ckpt_flat2d",             "Flat-2D Animerge",         "Checkpoint", "Flacher 2D Anime Stil"),
    ("ckpt_mistoonpikachu",     "MistoonsAnimeXL",          "Checkpoint", "Pikachu/Anime Stil"),
    ("ckpt_lyriel_v16",         "Lyriel v1.6",              "Checkpoint", "Fantasy Realism"),
    ("ckpt_meinaunreal",        "MeinaUnreal",              "Checkpoint", "Unreal-Engine Stil Anime"),
    ("ckpt_neverendingDream",   "NeverEnding Dream",        "Checkpoint", "Surrealistischer Traum"),
    ("ckpt_perfectdeliberate",  "Perfect Deliberate",       "Checkpoint", "Verfeinerte Deliberate"),
    ("ckpt_inkpunk",            "Inkpunk Diffusion",        "Checkpoint", "NFT/Punk Illustration"),
    ("ckpt_arcane_diffusion",   "Arcane Diffusion",         "Checkpoint", "League of Legends Arcane Stil"),
    ("ckpt_mo_di_diffusion",    "Mo Di Diffusion",          "Checkpoint", "Modern Disney Stil"),
    ("ckpt_roboetics",          "Robo-Diffusion",           "Checkpoint", "Roboter/Sci-Fi Stil"),
    ("ckpt_comic_babes",        "Comic Babes",              "Checkpoint", "Comic-Stil Figuren"),
    ("ckpt_icbinp",             "I Can't Believe It's Not Photo","Checkpoint","Fotorealismus"),
    ("ckpt_surreal_diffusion",  "Surreal Diffusion",        "Checkpoint", "Surrealismus Gemälde"),
    ("ckpt_protogenx34",        "Protogen x3.4",            "Checkpoint", "Sci-Fi Realismus"),
    ("ckpt_yiffymix",           "YiffyMix",                 "Checkpoint", "Furry Community Modell"),
    ("ckpt_manmarumix",         "ManMaruMix",               "Checkpoint", "Manga-Stil"),
    ("ckpt_abyssorangemix",     "AbyssOrangeMix",           "Checkpoint", "Anime Orange Tones"),
    ("ckpt_wd15_diffusion",     "WD 1.5 Beta",              "Checkpoint", "WaifuDiffusion 1.5"),
    ("ckpt_clarity",            "Clarity",                  "Checkpoint", "High-Detail Clarity"),
    ("ckpt_epicdream",          "EpicDream",                "Checkpoint", "Epische Traumlandschaften"),
    ("ckpt_fantasyworld",       "Fantasy World",            "Checkpoint", "Fantasy Umgebungen"),
    ("ckpt_landscapes",         "Landscapes",               "Checkpoint", "Naturlandschaften"),
    ("ckpt_architecturediff",   "Architecture Diffusion",   "Checkpoint", "Architektur-Visualisierung"),
    ("ckpt_furry_epoch",        "Furry Epoch",              "Checkpoint", "Furry Art Anime"),
    ("ckpt_babes_v20",          "Babes 2.0",                "Checkpoint", "Figuren-Fokus"),
    ("ckpt_cetus_mix",          "Cetus-Mix",                "Checkpoint", "Anime+Real Hybrid"),
    ("ckpt_freedom_v1",         "Freedom V1",               "Checkpoint", "Allzweck SD1.5"),
    ("ckpt_majicMIX",           "majicMIX realistic",       "Checkpoint", "Asiatisch-realistisch"),
    ("ckpt_chikmix",            "ChikMix",                  "Checkpoint", "Fotorealistisch Anime Mix"),
    ("ckpt_bra_v7",             "Beautiful Realistic Asians","Checkpoint","Asiatischer Porträt-Fokus"),
    ("ckpt_disneyPixarDiffusion","Disney Pixar Diffusion",  "Checkpoint", "Pixar 3D CGI Stil"),
    ("ckpt_stable_diffusion_v2","Stable Diffusion v2-768",  "Checkpoint", "SD2.0 768px"),
    ("ckpt_dreamshaper_v7",     "DreamShaper v7",           "Checkpoint", "Ältere DreamShaper Version"),
]

EXTENDED_CHECKPOINTS_XL = [
    # Mehr SDXL Checkpoints
    ("ckpt_albedobaseXL",       "AlbedoBase XL",            "Checkpoint", "Photo+Art Fusion XL"),
    ("ckpt_copaxTimelessXL",    "Copax TimeLess XL",        "Checkpoint", "Zeitloser Stil XL"),
    ("ckpt_dreamshaperXL_turbo","DreamShaper XL Turbo",     "Checkpoint", "Turbo DreamShaper XL"),
    ("ckpt_duchaitenXL",        "DucHaiten GameArt XL",     "Checkpoint", "Game Art Style XL"),
    ("ckpt_epicRealism_XL",     "Epic Realism XL",          "Checkpoint", "Ultra-Fotorealistisch XL"),
    ("ckpt_fenrirXL",           "Fenrir XL",                "Checkpoint", "Fantasy Realistisch XL"),
    ("ckpt_halcyon_XL",         "Halcyon XL",               "Checkpoint", "Filmisch XL"),
    ("ckpt_hellonijicute",      "Hellow Niji Cute",         "Checkpoint", "Cute Niji Anime XL"),
    ("ckpt_leosamsXL",          "Leosams HelloWorld XL",    "Checkpoint", "Allzweck XL"),
    ("ckpt_meinaXL",            "MeinaXL",                  "Checkpoint", "Anime XL Community"),
    ("ckpt_newrealityXL",       "New Reality XL",           "Checkpoint", "Fotorealistisch XL"),
    ("ckpt_nijiXL",             "Niji XL",                  "Checkpoint", "Niji Anime Stil XL"),
    ("ckpt_omnigenXL",          "OmniGen XL",               "Checkpoint", "Universell XL"),
    ("ckpt_picXL",              "PicX XL",                  "Checkpoint", "Fotografie XL"),
    ("ckpt_pixelwaveXL",        "PixelWave XL",             "Checkpoint", "Pixel+Wave Stil XL"),
    ("ckpt_prismXL",            "Prism XL",                 "Checkpoint", "Prismatischer Stil XL"),
    ("ckpt_raemuXL",            "RaemuXL",                  "Checkpoint", "Anime XL kompakt"),
    ("ckpt_samaritan3dXL",      "Samaritan 3D XL",         "Checkpoint", "3D Render Stil XL"),
    ("ckpt_sdvnXL",             "SDvN XL",                  "Checkpoint", "Neon Cyberpunk XL"),
    ("ckpt_spectrumblendXL",    "SpectrumBlend XL",         "Checkpoint", "Spectrum Merge XL"),
    ("ckpt_tpoxXL",             "TPOX XL",                  "Checkpoint", "Hyperrealistisch XL"),
    ("ckpt_turbovisionXL",      "TurboVision XL",           "Checkpoint", "Turbo Speed XL"),
    ("ckpt_ultrasharpXL",       "UltraSharp XL",            "Checkpoint", "Ultra-Scharf XL"),
    ("ckpt_vividlyXL",          "Vividly XL",               "Checkpoint", "Lebhafte Farben XL"),
    ("ckpt_wildcardXL",         "Wildcard XL",              "Checkpoint", "Zufallsstil XL"),
    ("ckpt_zovyaXL",            "Zovya RPG Artist",         "Checkpoint", "RPG Fantasy Art XL"),
    ("ckpt_openxl_base",        "OpenXL Base",              "Checkpoint", "Community SDXL Basis"),
    ("ckpt_waiANINSFWIllustrious","WAI-ANI Illustrious",   "Checkpoint", "Anime Illustrious Fine-tune"),
    ("ckpt_darkSushiMix_XL",    "DarkSushi Mix XL",        "Checkpoint", "Dunkler Anime Stil XL"),
    ("ckpt_ponyRealism",        "Pony Realism",             "Checkpoint", "Realismus auf Pony Basis"),
    ("ckpt_autismmixPony",      "AutismMix Pony",           "Checkpoint", "Anime Pony Community"),
    ("ckpt_prefectPonyXL",      "Prefect Pony XL",          "Checkpoint", "Verfeinert Pony XL"),
]

EXTENDED_LORAS = [
    # Detaillierte Stil-LoRAs
    ("lora_add_detail_v2",      "Add Detail v2",            "LoRAModel", "Detailschärfungs-LoRA v2"),
    ("lora_add_more_details",   "Add More Details",         "LoRAModel", "Mehr Texturen und Details"),
    ("lora_film_photography",   "Film Photography",         "LoRAModel", "Analog-Film Ästhetik"),
    ("lora_vintage_photo",      "Vintage Photo Style",      "LoRAModel", "Vintage Foto Look"),
    ("lora_dark_fantasy",       "Dark Fantasy",             "LoRAModel", "Dunkle Fantasy-Atmosphäre"),
    ("lora_light_fantasy",      "Light Fantasy",            "LoRAModel", "Helle Fantasy-Ästhetik"),
    ("lora_isometric",          "Isometric Style",          "LoRAModel", "Isometrische Perspektive"),
    ("lora_claymation",         "Claymation Style",         "LoRAModel", "Knetmasse-Animations-Stil"),
    ("lora_sticker_design",     "Sticker Design",           "LoRAModel", "Aufkleber/Sticker Stil"),
    ("lora_logo_design",        "Logo Design Style",        "LoRAModel", "Logo-Grafik Ästhetik"),
    ("lora_blueprint",          "Blueprint Style",          "LoRAModel", "Technische Zeichnung"),
    ("lora_neon_cyberpunk",     "Neon Cyberpunk",           "LoRAModel", "Neon + Cyberpunk Fusion"),
    ("lora_bioluminescent",     "Bioluminescent Style",     "LoRAModel", "Biolumineszenz-Effekte"),
    ("lora_vaporwave",          "Vaporwave Aesthetic",      "LoRAModel", "80s Vaporwave Ästhetik"),
    ("lora_synthwave",          "Synthwave Style",          "LoRAModel", "Synthwave Neon Grid"),
    ("lora_cottagecore",        "Cottagecore Style",        "LoRAModel", "Ländlich-gemütlicher Stil"),
    ("lora_darkroom",           "Darkroom Photography",     "LoRAModel", "Dunkelkammer Foto"),
    ("lora_studio_photo",       "Studio Photography",       "LoRAModel", "Professionelle Studiofotografie"),
    ("lora_food_photography",   "Food Photography",         "LoRAModel", "Kulinarische Fotografie"),
    ("lora_product_design",     "Product Design",           "LoRAModel", "Produktvisualisierung"),
    ("lora_interior_design",    "Interior Design",          "LoRAModel", "Innenarchitektur Stil"),
    ("lora_architectural_viz",  "Architectural Viz",        "LoRAModel", "Architektur-Visualisierung"),
    ("lora_concept_art",        "Concept Art Style",        "LoRAModel", "Konzeptkunst für Games/Film"),
    ("lora_matte_painting",     "Matte Painting",           "LoRAModel", "Film-Matte-Painting"),
    ("lora_book_illustration",  "Book Illustration",        "LoRAModel", "Buchillustrations-Stil"),
    ("lora_children_book",      "Children's Book Style",    "LoRAModel", "Kinderbuch-Illustration"),
    ("lora_manga_style",        "Manga Style",              "LoRAModel", "Japanischer Manga-Stil"),
    ("lora_manhwa_style",       "Manhwa Style",             "LoRAModel", "Koreanischer Manhwa-Stil"),
    ("lora_manhua_style",       "Manhua Style",             "LoRAModel", "Chinesischer Manhua-Stil"),
    ("lora_retro_anime_80s",    "Retro Anime 80s",          "LoRAModel", "80er Jahre Anime Stil"),
    ("lora_retro_anime_90s",    "Retro Anime 90s",          "LoRAModel", "90er Jahre Anime Stil"),
    ("lora_chibi_style",        "Chibi Style",              "LoRAModel", "Niedlicher Chibi-Miniatur"),
    ("lora_mecha_detail",       "Mecha Details",            "LoRAModel", "Roboter/Mecha Mechanik"),
    ("lora_game_icon",          "Game Icon Style",          "LoRAModel", "Spielsymbol-Ästhetik"),
    ("lora_ui_design",          "UI Design Style",          "LoRAModel", "Benutzeroberflächen-Design"),
    ("lora_bokeh_effect",       "Bokeh Effect",             "LoRAModel", "Optisches Unschärfe-Bokeh"),
    ("lora_golden_hour",        "Golden Hour Light",        "LoRAModel", "Goldene Stunde Beleuchtung"),
    ("lora_blue_hour",          "Blue Hour Photography",    "LoRAModel", "Blaue Stunde Foto"),
    ("lora_studio_lighting",    "Studio Lighting",          "LoRAModel", "Professionelle Studiobeleuchtung"),
    ("lora_rimlight",           "Rim Light Style",          "LoRAModel", "Gegenlicht Konturbeleuchtung"),
    ("lora_subsurface_scatter", "Subsurface Scattering",    "LoRAModel", "Hautdurchleuchtungs-Effekt"),
    ("lora_fur_texture",        "Fur Texture Detail",       "LoRAModel", "Fell-Textur Detailverbesserung"),
    ("lora_hair_detail",        "Hair Detail",              "LoRAModel", "Haarsträhnen-Detailschärfung"),
    ("lora_fabric_texture",     "Fabric Texture",           "LoRAModel", "Stoff-Textur Verbesserung"),
    ("lora_metal_material",     "Metal Material",           "LoRAModel", "Metall-Oberflächen-Rendering"),
    ("lora_glass_material",     "Glass Material",           "LoRAModel", "Glas-Transparenz-Effekt"),
    ("lora_water_rendering",    "Water Rendering",          "LoRAModel", "Wasser-Oberflächen-Simulation"),
    ("lora_fire_effect",        "Fire Effect",              "LoRAModel", "Feuer und Flammen Effekt"),
    ("lora_magic_effects",      "Magic Effects",            "LoRAModel", "Magische Partikeleffekte"),
    ("lora_explosion_sfx",      "Explosion VFX",            "LoRAModel", "Explosions-Spezialeffekte"),
    ("lora_cloud_detail",       "Cloud Detail",             "LoRAModel", "Wolken-Detailverbesserung"),
    ("lora_nature_detail",      "Nature Detail",            "LoRAModel", "Natur-Texturen Detail"),
    ("lora_urban_photography",  "Urban Photography",        "LoRAModel", "Stadtfotografie-Stil"),
    ("lora_street_photography", "Street Photography",       "LoRAModel", "Street-Photo Ästhetik"),
    ("lora_portraitenhancement","Portrait Enhancement",     "LoRAModel", "Porträt-Qualitätsverbesserung"),
    ("lora_age_slider",         "Age Slider",               "LoRAModel", "Alters-Kontroll-LoRA"),
    ("lora_weight_slider",      "Weight Slider",            "LoRAModel", "Gewichts-Kontroll-LoRA"),
    ("lora_expression_happy",   "Happy Expression",         "LoRAModel", "Glücklicher Gesichtsausdruck"),
    ("lora_expression_sad",     "Sad Expression",           "LoRAModel", "Trauriger Gesichtsausdruck"),
    ("lora_expression_angry",   "Angry Expression",         "LoRAModel", "Wütender Gesichtsausdruck"),
    ("lora_expression_surprise","Surprised Expression",     "LoRAModel", "Überraschter Ausdruck"),
    ("lora_pose_action",        "Action Pose",              "LoRAModel", "Dynamische Aktionsposen"),
    ("lora_pose_sitting",       "Sitting Pose",             "LoRAModel", "Sitzende Körperhaltungen"),
    ("lora_pose_lying",         "Lying Pose",               "LoRAModel", "Liegende Körperhaltungen"),
    ("lora_lighting_dramatic",  "Dramatic Lighting",        "LoRAModel", "Dramatische Beleuchtung"),
    ("lora_lighting_soft",      "Soft Box Lighting",        "LoRAModel", "Weiche Softbox-Beleuchtung"),
    ("lora_lighting_neon",      "Neon Lighting",            "LoRAModel", "Neon-Beleuchtungsszene"),
    # Flux-spezifische LoRAs
    ("lora_flux_detail_boost",  "Flux Detail Boost",        "LoRAModel", "Detail-Boost für Flux"),
    ("lora_flux_style_transfer","Flux Style Transfer",      "LoRAModel", "Stil-Transfer mit Flux"),
    ("lora_flux_portrait_v2",   "Flux Portrait v2",         "LoRAModel", "Porträt v2 für Flux"),
    ("lora_flux_landscape",     "Flux Landscape",           "LoRAModel", "Landschaft-LoRA für Flux"),
    ("lora_flux_texture_pack",  "Flux Texture Pack",        "LoRAModel", "Textur-Pack für Flux"),
    ("lora_flux_abstract",      "Flux Abstract",            "LoRAModel", "Abstrakte Kunst für Flux"),
    ("lora_flux_vintage",       "Flux Vintage Film",        "LoRAModel", "Vintage Film für Flux"),
    ("lora_flux_hyper_detail",  "Flux Hyper Detail",        "LoRAModel", "Maximale Details Flux"),
    ("lora_flux_dark_fantasy",  "Flux Dark Fantasy",        "LoRAModel", "Dunkle Fantasy für Flux"),
    ("lora_flux_ink_wash",      "Flux Ink Wash",            "LoRAModel", "Tuschemalerei für Flux"),
    # SDXL LoRAs
    ("lora_xl_add_detail",      "XL Add Detail",            "LoRAModel", "Detail-Boost für SDXL"),
    ("lora_xl_film_grain",      "XL Film Grain",            "LoRAModel", "Filmkorn für SDXL"),
    ("lora_xl_skin_real",       "XL Skin Realism",          "LoRAModel", "Hautdetail für SDXL"),
    ("lora_xl_face_detail",     "XL Face Detail",           "LoRAModel", "Gesichtsdetail für SDXL"),
    ("lora_xl_hair_detail",     "XL Hair Detail",           "LoRAModel", "Haardetail für SDXL"),
    ("lora_xl_clothes_detail",  "XL Clothes Detail",        "LoRAModel", "Kleidungsdetail für SDXL"),
    ("lora_xl_architecture",    "XL Architecture",          "LoRAModel", "Architektur-LoRA für SDXL"),
    ("lora_xl_portrait",        "XL Portrait Master",       "LoRAModel", "Porträt-Master für SDXL"),
    ("lora_xl_pony_addon",      "Pony Detail Addon",        "LoRAModel", "Detail-Addon für Pony XL"),
    ("lora_xl_illustrious_ref", "Illustrious Reference",    "LoRAModel", "Referenz-LoRA für Illustrious"),
]

EXTENDED_EMBEDDINGS = [
    ("emb_verybadimagenegative", "verybadimagenegative",   "Embedding", "Qualitätsverbesserungs-Negativ v1"),
    ("emb_ubbscore",            "UBBSCORE",                "Embedding", "UltraBeauty Score Positiv"),
    ("emb_score_9",             "score_9",                 "Embedding", "Qualitätsscore Embedding"),
    ("emb_score_8_up",          "score_8_up",              "Embedding", "Score >= 8 Positiv"),
    ("emb_source_anime",        "source_anime",            "Embedding", "Anime-Quell-Stil"),
    ("emb_source_pony",         "source_pony",             "Embedding", "Pony-Quell-Stil"),
    ("emb_worst_quality",       "worst_quality",           "Embedding", "Schlechteste Qualität Negativ"),
    ("emb_low_quality",         "low_quality",             "Embedding", "Niedrige Qualität Negativ"),
    ("emb_fastNegfixedcompact", "FastNegative-compact",    "Embedding", "Schnelles Negativ-Embedding"),
    ("emb_boring_e621",         "boring_e621_fluffyart",   "Embedding", "Langweilig Negativ e621"),
    ("emb_badhandv4",           "bad_hands_v4",            "Embedding", "Hände v4 Negativ"),
    ("emb_clothes_negative",    "clothes_negative",        "Embedding", "Kleidungs-Fehler Negativ"),
    ("emb_mutated_hands",       "mutated_hands",           "Embedding", "Mutierte Hände Negativ"),
    ("emb_ugly_face",           "ugly_face",               "Embedding", "Hässliches Gesicht Negativ"),
    ("emb_deformed_body",       "deformed_body",           "Embedding", "Deformierter Körper Negativ"),
    ("emb_easyneg_v10",         "EasyNeg v10",             "Embedding", "EasyNeg Version 10"),
    ("emb_neg_feet",            "negative_feet",           "Embedding", "Füße Fehler Negativ"),
    ("emb_negative_hand",       "negative_hand",           "Embedding", "Hand Negativ"),
    ("emb_bad_prompt_v2",       "bad_prompt_v2",           "Embedding", "Fehlerhafte Prompts Negativ"),
    ("emb_watermark_neg",       "watermark_removal",       "Embedding", "Wasserzeichen Entfernung Negativ"),
    ("emb_deepred_v2",          "deep_negative_v1",        "Embedding", "Tiefen Negativ v1"),
    ("emb_textfix",             "TextFix",                 "Embedding", "Text-Rendering Verbesserung"),
]

EXTENDED_CONTROLNET = [
    # Flux ControlNet Erweiterungen
    ("cn_flux_pose",        "Flux ControlNet Pose",         "ControlNetModel", "Pose für Flux"),
    ("cn_flux_tile",        "Flux ControlNet Tile",         "ControlNetModel", "Tile für Flux"),
    ("cn_flux_lineart",     "Flux ControlNet Lineart",      "ControlNetModel", "Lineart für Flux"),
    ("cn_flux_scribble",    "Flux ControlNet Scribble",     "ControlNetModel", "Scribble für Flux"),
    ("cn_flux_mlsd",        "Flux ControlNet MLSD",         "ControlNetModel", "MLSD für Flux"),
    # SD3 ControlNet
    ("cn_sd3_canny",        "SD3 ControlNet Canny",         "ControlNetModel", "Canny für SD3"),
    ("cn_sd3_depth",        "SD3 ControlNet Depth",         "ControlNetModel", "Depth für SD3"),
    # Spezialisierte ControlNet Modelle
    ("cn_soft_edge",        "ControlNet Soft Edge",         "ControlNetModel", "Weiche Kanten Detektion"),
    ("cn_hand_refiner",     "ControlNet Hand Refiner",      "ControlNetModel", "Hand-Verfeinerung"),
    ("cn_face_landmark",    "ControlNet Face Landmark",     "ControlNetModel", "Gesichts-Orientierungspunkte"),
    ("cn_qr_pattern",       "ControlNet QR Pattern",        "ControlNetModel", "QR-Code Integration"),
    ("cn_brightness",       "ControlNet Brightness",        "ControlNetModel", "Helligkeits-Konditionierung"),
    ("cn_colorize",         "ControlNet Colorization",      "ControlNetModel", "Kolorierungs-Konditionierung"),
    ("cn_inpaint_xl",       "ControlNet Inpaint XL",        "ControlNetModel", "Inpainting für SDXL"),
    ("cn_tile_xl",          "ControlNet Tile XL",           "ControlNetModel", "Tile für SDXL"),
    ("cn_scribble_xl",      "ControlNet Scribble XL",       "ControlNetModel", "Scribble für SDXL"),
    ("cn_softedge_xl",      "ControlNet SoftEdge XL",       "ControlNetModel", "Soft Edge für SDXL"),
    ("cn_lineart_xl",       "ControlNet Lineart XL",        "ControlNetModel", "Lineart für SDXL"),
    ("cn_shuffle_xl",       "ControlNet Shuffle XL",        "ControlNetModel", "Shuffle für SDXL"),
    ("cn_holistically",     "Holistically-Attracted",       "ControlNetModel", "HAT Pose Detektion"),
    ("cn_wholebodydw",      "DWPose Wholebody",             "ControlNetModel", "Ganzkörper DWPose"),
    ("cn_animatediff_cn",   "AnimateDiff ControlNet",       "ControlNetModel", "ControlNet für Animation"),
    ("cn_svd_cn",           "SVD ControlNet",               "ControlNetModel", "Video ControlNet"),
]

COMFYUI_CUSTOM_NODES = [
    ("cn_pack_comfyroll",       "ComfyRoll Custom Nodes",       "CustomNodePack", "Erweiterter Utility Pack"),
    ("cn_pack_efficiency",      "ComfyUI Efficiency Nodes",     "CustomNodePack", "Effiziente Pipeline Nodes"),
    ("cn_pack_impact",          "ComfyUI Impact Pack",          "CustomNodePack", "Face/Object Detailer"),
    ("cn_pack_ultimate",        "Ultimate SD Upscale",          "CustomNodePack", "Upscale Knoten"),
    ("cn_pack_controlnet_aux",  "ControlNet Auxiliary",         "CustomNodePack", "ControlNet Preprocessor"),
    ("cn_pack_animatediff",     "AnimateDiff Evolved",          "CustomNodePack", "Video Animation Nodes"),
    ("cn_pack_was",             "WAS Node Suite",               "CustomNodePack", "Erweitertes Utility-Set"),
    ("cn_pack_rgthree",         "rgthree Nodes",                "CustomNodePack", "Power Workflow Nodes"),
    ("cn_pack_manager",         "ComfyUI Manager",              "CustomNodePack", "Extension Manager"),
    ("cn_pack_inspire",         "ComfyUI Inspire Pack",         "CustomNodePack", "Inspire Utility Nodes"),
    ("cn_pack_ipadapter_plus",  "IPAdapter Plus",               "CustomNodePack", "Erweiterter IP-Adapter"),
    ("cn_pack_pulid",           "PuLID ComfyUI",                "CustomNodePack", "ID Konsistenz Nodes"),
    ("cn_pack_ltxvideo",        "ComfyUI-LTXVideo",             "CustomNodePack", "LTX-Video Nodes"),
    ("cn_pack_wan",             "ComfyUI-WAN",                  "CustomNodePack", "WAN Video Nodes"),
    ("cn_pack_florence2",       "Florence2",                    "CustomNodePack", "Florence2 Vision Knoten"),
    ("cn_pack_clip_seg",        "CLIP Segmentation",            "CustomNodePack", "CLIP-basierte Segmentierung"),
    ("cn_pack_layerdiffuse",    "LayerDiffuse",                 "CustomNodePack", "Ebenen-Transparency"),
    ("cn_pack_ic_light",        "IC-Light",                     "CustomNodePack", "Relighting Nodes"),
    ("cn_pack_inpaint_crop",    "Inpaint Cropand Stitch",       "CustomNodePack", "Intelligentes Inpainting"),
    ("cn_pack_reactor",         "ReActor",                      "CustomNodePack", "Face Swap Nodes"),
    ("cn_pack_segment_any",     "Segment Anything",             "CustomNodePack", "SAM Segmentierung"),
    ("cn_pack_depthanything",   "Depth Anything",               "CustomNodePack", "Tiefenschätzung Nodes"),
    ("cn_pack_openpose",        "OpenPose Editor",              "CustomNodePack", "Pose Editor Nodes"),
    ("cn_pack_onebutton",       "One Button Prompt",            "CustomNodePack", "Auto-Prompt Generator"),
    ("cn_pack_dynamicprompts",  "Dynamic Prompts",              "CustomNodePack", "Dynamische Prompt-Nodes"),
    ("cn_pack_noisetools",      "Noise Tools",                  "CustomNodePack", "Rauschmanipulations-Nodes"),
    ("cn_pack_latentblend",     "Latent Blend",                 "CustomNodePack", "Latent-Blend Nodes"),
    ("cn_pack_mbw",             "Model Block Weight",           "CustomNodePack", "Modell-Gewichts-Blending"),
    ("cn_pack_patchwork",       "Patchwork Nodes",              "CustomNodePack", "Kachel-Workflow Nodes"),
    ("cn_pack_audioreactive",   "AudioReactive",                "CustomNodePack", "Audio-Reaktive Nodes"),
    ("cn_pack_svd",             "ComfyUI SVD",                  "CustomNodePack", "Stable Video Diffusion"),
    ("cn_pack_clipseg",         "CLIPSeg",                      "CustomNodePack", "Text-geführte Segmentierung"),
    ("cn_pack_blip",            "BLIP Nodes",                   "CustomNodePack", "Bildunterschriften Nodes"),
    ("cn_pack_wd14",            "WD14 Tagger",                  "CustomNodePack", "Automatisches Tag-System"),
    ("cn_pack_color_matching",  "Color Matching",               "CustomNodePack", "Farbanpassungs-Nodes"),
    ("cn_pack_advanced_encode", "Advanced CLIP Encoding",       "CustomNodePack", "Erweiterte Textkodierung"),
    ("cn_pack_photoshop_plugin","Photoshop Plugin",             "CustomNodePack", "Photoshop Integration"),
    ("cn_pack_frameinterp",     "Frame Interpolation",          "CustomNodePack", "Frame-Interpolation Video"),
    ("cn_pack_videohelper",     "Video Helper Suite",           "CustomNodePack", "Video-Verarbeitungs-Nodes"),
    ("cn_pack_image_resize",    "Image Resize",                 "CustomNodePack", "Bildgrößenänderungs-Nodes"),
    ("cn_pack_face_analysis",   "Face Analysis",                "CustomNodePack", "Gesichtsanalyse-Nodes"),
    ("cn_pack_canny_edge",      "Canny Edge",                   "CustomNodePack", "Canny-Kanten Nodes"),
    ("cn_pack_tiled_ksampler",  "Tiled KSampler",               "CustomNodePack", "Kachel-Sampling Nodes"),
    ("cn_pack_model_merger",    "Model Merger",                 "CustomNodePack", "Modell-Merge Nodes"),
    ("cn_pack_cutoff",          "Cutoff",                       "CustomNodePack", "Token-Cutoff Nodes"),
    ("cn_pack_prompt_control",  "Prompt Control",               "CustomNodePack", "Erweiterte Prompt-Kontrolle"),
    ("cn_pack_power_noise",     "Power Noise Suite",            "CustomNodePack", "Rausch-Generator Nodes"),
    ("cn_pack_3d_viewer",       "3D Mesh Viewer",               "CustomNodePack", "3D Modell Viewer"),
    ("cn_pack_lora_selector",   "LoRA Selector",                "CustomNodePack", "LoRA Auswahlknoten"),
    ("cn_pack_checkpoint_merger","Checkpoint Merger",           "CustomNodePack", "Checkpoint Merge Nodes"),
    ("cn_pack_kohya_hrfix",     "Kohya HiRes Fix",              "CustomNodePack", "Kohya-Style HiRes"),
    ("cn_pack_batch_processing","Batch Processing",             "CustomNodePack", "Stapelverarbeitungs-Nodes"),
]

PROMPT_TECHNIQUES = [
    ("pt_attention_syntax",     "Attention Syntax (a:w)",   "PromptTechnique", "Gewichteter Token (word:1.5)"),
    ("pt_emphasis",             "Emphasis Brackets",        "PromptTechnique", "Hervorhebung mit (( ))"),
    ("pt_de_emphasis",          "De-emphasis Brackets",     "PromptTechnique", "Schwächung mit [ ]"),
    ("pt_alternation",          "Alternation Syntax",       "PromptTechnique", "Token-Wechsel [A|B]"),
    ("pt_schedule",             "Prompt Scheduling",        "PromptTechnique", "Zeitgesteuerte Token [A:B:0.5]"),
    ("pt_andcondition",         "AND Conditioning",         "PromptTechnique", "Separate Conditioning-Stränge"),
    ("pt_prompt_editing",       "Prompt Editing",           "PromptTechnique", "Stepbasierter Prompt-Wechsel"),
    ("pt_negative_weighting",   "Negative Weighting",       "PromptTechnique", "Negative Token-Gewichtung"),
    ("pt_embeddings_in_prompt", "Embedding Usage",          "PromptTechnique", "Embeddings im Prompt verwenden"),
    ("pt_lora_in_prompt",       "LoRA in Prompt",           "PromptTechnique", "<lora:name:strength> Syntax"),
    ("pt_hypernetwork_prompt",  "Hypernetwork Activation",  "PromptTechnique", "Hypernetwork-Aktivierung"),
    ("pt_keyword_density",      "Keyword Density",          "PromptTechnique", "Optimale Keyword-Dichte"),
    ("pt_trigger_words",        "Trigger Words",            "PromptTechnique", "Modell-spezifische Auslösewörter"),
    ("pt_quality_tokens",       "Quality Tokens",           "PromptTechnique", "masterpiece, best quality etc."),
    ("pt_negative_quality",     "Negative Quality Tokens",  "PromptTechnique", "worst quality, blurry etc."),
    ("pt_artist_prompting",     "Artist Name Prompting",    "PromptTechnique", "Künstlernamen als Stilreferenz"),
    ("pt_style_transfer_prompt","Style Transfer Prompting", "PromptTechnique", "In the style of... Syntax"),
    ("pt_scene_description",    "Scene Description",        "PromptTechnique", "Szenenbeschreibungs-Aufbau"),
    ("pt_camera_angles",        "Camera Angle Tokens",      "PromptTechnique", "Kamerawinkel-Spezifikation"),
    ("pt_lighting_tokens",      "Lighting Tokens",          "PromptTechnique", "Beleuchtungs-Token-Set"),
    ("pt_composition_tokens",   "Composition Tokens",       "PromptTechnique", "Kompositions-Spezifikation"),
    ("pt_color_palette",        "Color Palette Prompting",  "PromptTechnique", "Farbpaletten-Steuerung"),
    ("pt_aspect_ratio_token",   "Aspect Ratio Tokens",      "PromptTechnique", "Seitenverhältnis-Beeinflussung"),
    ("pt_resolution_token",     "Resolution Quality Tokens","PromptTechnique", "Auflösungsqualitäts-Token"),
    ("pt_negative_space",       "Negative Space Prompt",    "PromptTechnique", "Freiraum-Kompositions-Prompt"),
    ("pt_charact_consistency",  "Character Consistency",    "PromptTechnique", "Konsistente Figuren-Prompt"),
    ("pt_promptbook",           "Prompt Book Approach",     "PromptTechnique", "Strukturiertes Prompt-System"),
    ("pt_meta_prompting",       "Meta-Prompting",           "PromptTechnique", "LLM-generierte Prompts"),
    ("pt_chain_of_thought",     "Chain-of-Thought Prompt",  "PromptTechnique", "Schrittweise Bildaufbau"),
    ("pt_multimodal_cond",      "Multimodal Conditioning",  "PromptTechnique", "Text + Bild Konditionierung"),
    ("pt_cross_attn_inject",    "Cross-Attention Injection","PromptTechnique", "Attention-Injektion Technik"),
    ("pt_prompt_interpolation", "Prompt Interpolation",     "PromptTechnique", "Schrittweise Prompt-Übergänge"),
    ("pt_region_prompting",     "Region-Based Prompting",   "PromptTechnique", "Regionen-spezifisches Prompting"),
    ("pt_composable_diffusion", "Composable Diffusion",     "PromptTechnique", "Komposierbare Diffusion"),
    ("pt_break_keyword",        "BREAK Keyword",            "PromptTechnique", "Attention-Reset mit BREAK"),
    ("pt_flux_guidance",        "Flux Guidance Scale",      "PromptTechnique", "Flux-spezifische Guidance"),
    ("pt_t5_prompting",         "T5 Long-form Prompting",   "PromptTechnique", "Langer Satz-Prompt für T5"),
    ("pt_natural_language",     "Natural Language Prompt",  "PromptTechnique", "Natürliche Sprache vs. Tags"),
    ("pt_booru_tags",           "Booru Tag Style",          "PromptTechnique", "Anime Booru Tag System"),
    ("pt_danbooru_syntax",      "Danbooru Syntax",          "PromptTechnique", "Danbooru Keyword-Stil"),
]

IMAGE_WORKFLOWS = [
    ("wf_txt2img_basic",        "Basic Txt2Img Workflow",   "Workflow", "Einfacher Text-zu-Bild"),
    ("wf_img2img_basic",        "Basic Img2Img Workflow",   "Workflow", "Einfacher Bild-zu-Bild"),
    ("wf_inpainting_basic",     "Basic Inpainting",         "Workflow", "Einfaches Inpainting"),
    ("wf_outpainting",          "Outpainting Workflow",     "Workflow", "Bild-Erweiterung"),
    ("wf_hires_fix",            "HiRes Fix Workflow",       "Workflow", "Hochauflösungs-Workflow"),
    ("wf_upscale_chain",        "Upscale Chain",            "Workflow", "Mehrstufiges Upscaling"),
    ("wf_controlnet_chain",     "ControlNet Chain",         "Workflow", "Multi-ControlNet Pipeline"),
    ("wf_face_swap",            "Face Swap Workflow",       "Workflow", "Gesichtstausch-Pipeline"),
    ("wf_face_restore",         "Face Restoration",         "Workflow", "Gesichtswiederherstellung"),
    ("wf_portrait_pipeline",    "Portrait Pipeline",        "Workflow", "Vollständige Porträt-Pipeline"),
    ("wf_product_photo",        "Product Photography",      "Workflow", "Produktfoto-Workflow"),
    ("wf_video_generation",     "Video Generation",         "Workflow", "Video-Generierungs-Workflow"),
    ("wf_video_interpolation",  "Video Interpolation",      "Workflow", "Video Frame-Interpolation"),
    ("wf_video_upscale",        "Video Upscaling",          "Workflow", "Video-Upscaling-Pipeline"),
    ("wf_style_transfer",       "Style Transfer",           "Workflow", "Stil-Transfer-Workflow"),
    ("wf_sketch_to_image",      "Sketch to Image",          "Workflow", "Skizze zu Bild"),
    ("wf_anime_colorize",       "Anime Colorization",       "Workflow", "Anime Kolorierungs-Workflow"),
    ("wf_architecture_viz",     "Architecture Visualization","Workflow","Architektur-Visualisierungs-Workflow"),
    ("wf_batch_generate",       "Batch Generation",         "Workflow", "Massen-Generierungs-Workflow"),
    ("wf_prompt_from_image",    "Prompt from Image",        "Workflow", "Reverse-Prompting"),
    ("wf_lora_training_prep",   "LoRA Training Prep",       "Workflow", "Datenvorbereitung für LoRA"),
    ("wf_dataset_caption",      "Dataset Captioning",       "Workflow", "Auto-Captioning für Datasets"),
    ("wf_model_merge",          "Model Merge Workflow",     "Workflow", "Modell-Merge-Workflow"),
    ("wf_lcm_turbo",            "LCM Turbo Workflow",       "Workflow", "Schnelle LCM-Generierung"),
    ("wf_flux_standard",        "Flux Standard Workflow",   "Workflow", "Standard Flux-Workflow"),
    ("wf_flux_ip_adapter",      "Flux IP-Adapter",          "Workflow", "Flux mit IP-Adapter"),
    ("wf_flux_redux",           "Flux Redux Style",         "Workflow", "Flux Redux Style Transfer"),
    ("wf_flux_kontext",         "Flux Kontext Workflow",    "Workflow", "Flux Kontext-Referenz"),
    ("wf_sdxl_refiner",         "SDXL + Refiner",           "Workflow", "SDXL Base + Refiner Pipeline"),
    ("wf_animatediff",          "AnimateDiff Workflow",     "Workflow", "AnimateDiff Video-Workflow"),
    ("wf_wan_t2v",              "WAN T2V Workflow",         "Workflow", "WAN Text-zu-Video"),
    ("wf_wan_i2v",              "WAN I2V Workflow",         "Workflow", "WAN Bild-zu-Video"),
    ("wf_ltxv_workflow",        "LTX-Video Workflow",       "Workflow", "LTX-Video Generierung"),
    ("wf_cogvideo_workflow",    "CogVideoX Workflow",       "Workflow", "CogVideoX Generierung"),
    ("wf_sam_segmentation",     "SAM Segmentation",         "Workflow", "Segment Anything Workflow"),
    ("wf_layerdiffuse",         "LayerDiffuse Workflow",    "Workflow", "Transparenz-Ebenen"),
    ("wf_ic_light",             "IC-Light Relight",         "Workflow", "Relighting-Workflow"),
    ("wf_pulid_consistency",    "PuLID Consistency",        "Workflow", "ID-konsistenter Workflow"),
    ("wf_regional_prompt",      "Regional Prompt",          "Workflow", "Regionen-Prompt-Workflow"),
    ("wf_photoreal_portrait",   "Photorealistic Portrait",  "Workflow", "Fotorealistisches Porträt"),
    ("wf_concept_art_gen",      "Concept Art Generation",   "Workflow", "Konzeptkunst-Erstellung"),
    ("wf_game_asset",           "Game Asset Generation",    "Workflow", "Spielasset-Generierung"),
    ("wf_logo_generation",      "Logo Generation",          "Workflow", "Logo-Erstellungs-Workflow"),
    ("wf_icon_sheet",           "Icon Sheet Generation",    "Workflow", "Iconset-Generierungs-Workflow"),
    ("wf_texture_generation",   "Texture Generation",       "Workflow", "Textur-Generierungs-Workflow"),
    ("wf_seamless_tile",        "Seamless Tile Texture",    "Workflow", "Nahtlose Kachel-Textur"),
    ("wf_panorama",             "Panorama Generation",      "Workflow", "360° Panorama-Generierung"),
    ("wf_isometric_scene",      "Isometric Scene",          "Workflow", "Isometrische Szene"),
    ("wf_character_turnaround", "Character Turnaround",     "Workflow", "Charakter-Drehtisch 360°"),
    ("wf_adetailer_auto",       "ADetailer Auto Fix",       "Workflow", "Automatische Detailkorrektur"),
]

MODEL_PLATFORMS = [
    ("plat_civitai",        "CivitAI Platform",         "Platform", "Größte SD Modell-Community"),
    ("plat_huggingface",    "HuggingFace Hub",          "Platform", "ML Model Repository"),
    ("plat_github",         "GitHub",                   "Platform", "Open-Source Code Hosting"),
    ("plat_discord_comfy",  "ComfyUI Discord",          "Platform", "ComfyUI Community Server"),
    ("plat_discord_sd",     "SD Discord",               "Platform", "Stable Diffusion Discord"),
    ("plat_reddit_sd",      "r/StableDiffusion",        "Platform", "SD Reddit Community"),
    ("plat_reddit_civitai", "r/CivitAI",                "Platform", "CivitAI Reddit"),
    ("plat_openart",        "OpenArt",                  "Platform", "KI-Kunst Community"),
    ("plat_lexica",         "Lexica",                   "Platform", "Prompt-Suchmaschine"),
    ("plat_prompthero",     "PromptHero",               "Platform", "Prompt-Inspirations-Plattform"),
    ("plat_krea_ai",        "Krea AI",                  "Platform", "Echtzeit-Generierung"),
    ("plat_tensor_art",     "TensorArt",                "Platform", "Online Modell-Training"),
    ("plat_seaart",         "SeaArt",                   "Platform", "Asiatische SD Community"),
    ("plat_liblibai",       "Liblib AI",                "Platform", "Chinesische SD Plattform"),
    ("plat_novelai",        "NovelAI",                  "Platform", "Anime-Geschichten und Bilder"),
    ("plat_naifu",          "NAIFU",                    "Platform", "NovelAI-basierte Community"),
    ("plat_playgroundai",   "Playground AI",            "Platform", "Browser-basiertes SD"),
    ("plat_leonardo",       "Leonardo AI",              "Platform", "Fine-tuned SD Plattform"),
    ("plat_stablediffusion_online","StableDiffusion Online","Platform","Online SD Interface"),
    ("plat_dezgo",          "Dezgo",                    "Platform", "Einfaches Online-SD"),
    ("plat_clipdrop",       "ClipDrop",                 "Platform", "Stability AI Web-Tools"),
    ("plat_dreamstudio",    "DreamStudio",              "Platform", "Stability AI Official"),
    ("plat_runpod",         "RunPod",                   "Platform", "Cloud GPU für SD"),
    ("plat_vastai",         "Vast.ai",                  "Platform", "GPU Rental Marketplace"),
    ("plat_replicate",      "Replicate",                "Platform", "ML Model API Plattform"),
    ("plat_fal_ai",         "fal.ai",                   "Platform", "Schnelle Inferenz API"),
    ("plat_together_ai",    "Together AI",              "Platform", "Distributed AI Inference"),
    ("plat_comfy_cloud",    "ComfyUI Cloud",            "Platform", "Gehostetes ComfyUI"),
]

IMAGE_FORMATS_TECH = [
    ("fmt_png",             "PNG",                      "FileFormat", "Verlustfreies Bildformat"),
    ("fmt_jpg",             "JPEG",                     "FileFormat", "Verlustbehaftetes Bildformat"),
    ("fmt_webp",            "WebP",                     "FileFormat", "Modernes Webformat"),
    ("fmt_safetensors",     "SafeTensors",              "FileFormat", "Sicheres ML-Gewichtsformat"),
    ("fmt_ckpt",            "CKPT",                     "FileFormat", "PyTorch Checkpoint"),
    ("fmt_gguf",            "GGUF",                     "FileFormat", "llama.cpp Format"),
    ("fmt_pt",              "PT",                       "FileFormat", "PyTorch Tensor Format"),
    ("fmt_bin",             "BIN",                      "FileFormat", "Binäres Modellformat"),
    ("fmt_diffusers_dir",   "Diffusers Directory",      "FileFormat", "HuggingFace Verzeichnisformat"),
    ("fmt_onnx",            "ONNX",                     "FileFormat", "Open Neural Network Exchange"),
    ("fmt_ncnn",            "NCNN",                     "FileFormat", "Tencent Mobile Inference"),
    ("fmt_coreml",          "CoreML",                   "FileFormat", "Apple CoreML Format"),
    ("fmt_exif",            "EXIF Metadata",            "FileFormat", "Bild-Metadaten Format"),
    ("fmt_civitai_meta",    "CivitAI Metadata",         "FileFormat", "CivitAI PNG Metadaten"),
    ("fmt_workflow_json",   "Workflow JSON",            "FileFormat", "ComfyUI Workflow Datei"),
    ("fmt_smproj",          "SMPROJ",                   "FileFormat", "StableSwarmUI Projektdatei"),
]

AI_CONCEPTS = [
    ("concept_diffusion",   "Diffusion Process",        "Concept", "Iterativer Rauschentfernungsprozess"),
    ("concept_latent_space","Latent Space",             "Concept", "Komprimierter Merkmalsraum"),
    ("concept_attention",   "Attention Mechanism",      "Concept", "Self-/Cross-Attention in Transformers"),
    ("concept_cfgscale",    "CFG Scale",                "Concept", "Classifier-Free Guidance Stärke"),
    ("concept_steps",       "Inference Steps",          "Concept", "Anzahl der Denoising-Iterationen"),
    ("concept_seed",        "Random Seed",              "Concept", "Zufallszahl für Reproduzierbarkeit"),
    ("concept_prompt",      "Text Prompt",              "Concept", "Texteingabe zur Bildsteuerung"),
    ("concept_neg_prompt",  "Negative Prompt",          "Concept", "Unerwünschte Elemente ausschließen"),
    ("concept_inpainting",  "Inpainting",               "Concept", "Selektives Neugenerieren von Bereichen"),
    ("concept_outpainting", "Outpainting",              "Concept", "Bild über Grenzen erweitern"),
    ("concept_img2img",     "Image-to-Image",           "Concept", "Bildtransformation mit Denoise-Stärke"),
    ("concept_txt2img",     "Text-to-Image",            "Concept", "Textbasierte Bildgenerierung"),
    ("concept_hiresfix",    "Hires Fix",                "Concept", "Hochauflösungs-Nachbearbeitung"),
    ("concept_adetailer",   "Auto Detailer",            "Concept", "Automatische Gesichts/Hand-Detailierung"),
    ("concept_cfg_rescale", "CFG Rescale",              "Concept", "Übersteuerungskorrektur-Technik"),
    ("concept_perp_neg",    "Perpendicular Negative",   "Concept", "Senkrechte Negativführung"),
    ("concept_pag",         "Perturbed Attention",      "Concept", "Perturbed Attention Guidance"),
    ("concept_apg",         "Adaptive Projected Guidance","Concept","Adaptiver Guidance Mechanismus"),
    ("concept_sag",         "Self-Attention Guidance",  "Concept", "Selbstaufmerksamkeit-Führung"),
    ("concept_igs",         "Inverted Guidance Scale",  "Concept", "Invertierter Guidance Scale"),
    ("concept_quantization","Quantization",             "Concept", "Modellkompression (FP16/BF16/INT8)"),
    ("concept_flash_attn",  "Flash Attention",          "Concept", "Speicher-effiziente Attention"),
    ("concept_xformers",    "xFormers",                 "Concept", "Effiziente Transformer-Operationen"),
    ("concept_triton",      "Triton Kernels",           "Concept", "GPU-Kernel für ML-Operationen"),
    ("concept_vram_opt",    "VRAM Optimization",        "Concept", "Speichersparen durch Offloading"),
    ("concept_tile_vae",    "Tiled VAE",                "Concept", "Kachel-basiertes VAE Decoding"),
    ("concept_lcm_sampling","LCM Sampling",             "Concept", "Konsistenz-Modell Sampling"),
    ("concept_distillation","Model Distillation",       "Concept", "Wissensübertragung Teacher->Student"),
    ("concept_merge",       "Model Merging",            "Concept", "LERP/SLERP Modell-Interpolation"),
    ("concept_prune",       "Model Pruning",            "Concept", "Modellkompression durch Gewichtsentfernung"),
    ("concept_fp16",        "FP16 Precision",           "Concept", "Halbpräzisions-Gleitkomma"),
    ("concept_bf16",        "BF16 Precision",           "Concept", "Brain Float 16 Format"),
    ("concept_fp8",         "FP8 Precision",            "Concept", "8-bit Float Quantisierung"),
    ("concept_int8",        "INT8 Quantization",        "Concept", "Ganzzahlige 8-bit Quantisierung"),
    ("concept_gguf",        "GGUF Format",              "Concept", "llama.cpp kompatibles Format"),
    ("concept_safetensors", "SafeTensors Format",       "Concept", "Sicheres Tensor-Speicherformat"),
    ("concept_ckpt",        "CKPT Format",              "Concept", "PyTorch Checkpoint Format"),
    ("concept_clip_skip",   "CLIP Skip",                "Concept", "CLIP Layer Überspringen"),
    ("concept_token",       "Token",                    "Concept", "Einheit der Texttokenisierung"),
    ("concept_embedding_vec","Embedding Vector",        "Concept", "Numerische Vektordarstellung"),
]

HARDWARE_PLATFORMS = [
    ("hw_nvidia_rtx4090",   "NVIDIA RTX 4090",      "Hardware", "Flaggschiff Consumer GPU"),
    ("hw_nvidia_rtx4080",   "NVIDIA RTX 4080",      "Hardware", "High-End Consumer GPU"),
    ("hw_nvidia_rtx4070",   "NVIDIA RTX 4070",      "Hardware", "Mid-High Consumer GPU"),
    ("hw_nvidia_rtx3090",   "NVIDIA RTX 3090",      "Hardware", "Vorgänger Flaggschiff"),
    ("hw_nvidia_a100",      "NVIDIA A100",          "Hardware", "Datacenter Training GPU"),
    ("hw_nvidia_h100",      "NVIDIA H100",          "Hardware", "Nächste Gen Datacenter GPU"),
    ("hw_nvidia_l40s",      "NVIDIA L40S",          "Hardware", "Professionelle Inferenz GPU"),
    ("hw_amd_rx7900xtx",    "AMD RX 7900 XTX",      "Hardware", "AMD Flaggschiff Consumer GPU"),
    ("hw_amd_rx6800xt",     "AMD RX 6800 XT",       "Hardware", "AMD High-End GPU"),
    ("hw_amd_mi300x",       "AMD MI300X",           "Hardware", "AMD Datacenter GPU"),
    ("hw_apple_m3max",      "Apple M3 Max",         "Hardware", "Apple Silicon Neural Engine"),
    ("hw_intel_arc_a770",   "Intel Arc A770",       "Hardware", "Intel Dedicated GPU"),
    ("hw_cuda",             "CUDA",                 "Hardware", "NVIDIA GPU Computing Platform"),
    ("hw_rocm",             "ROCm",                 "Hardware", "AMD GPU Computing Platform"),
    ("hw_directml",         "DirectML",             "Hardware", "Windows ML Backend"),
    ("hw_metal",            "Metal",                "Hardware", "Apple GPU Compute API"),
    ("hw_openvino",         "OpenVINO",             "Hardware", "Intel Neural Network Inference"),
    ("hw_onnx",             "ONNX Runtime",         "Hardware", "Cross-Platform ML Inference"),
    ("hw_tensorrt",         "TensorRT",             "Hardware", "NVIDIA Optimized Inference"),
    ("hw_cloud_a100",       "Cloud A100 Instance",  "Hardware", "Google Colab / Lambda etc."),
]

def make_id(s):
    """Konvertiert String zu gültigem ID"""
    return re.sub(r'[^a-z0-9_]', '_', s.lower())[:60]

# ─────────────────────────────────────────────────────────────────────────────
# GRAPH AUFBAU
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    nodes = {}  # id -> {id, label, type, description}
    edges = []  # {source, target, relation, weight}

    def add_node(nid, label, ntype, desc=""):
        nodes[nid] = {"id": nid, "label": label, "type": ntype, "description": desc}

    def add_edge(src, tgt, rel, weight=1.0):
        if src in nodes and tgt in nodes:
            edges.append({"source": src, "target": tgt, "relation": rel, "weight": weight})

    # Alle Knoten hinzufügen
    for entry in (ORGANIZATIONS + ARCHITECTURES + BASE_MODELS + MODEL_TYPES +
                  WEBUIS + TRAINING_FRAMEWORKS + DATASETS + CONTROLNET_MODELS +
                  UPSCALERS + POPULAR_CHECKPOINTS + LORA_STYLES + EMBEDDINGS +
                  SAMPLERS + SCHEDULERS + EXTENSIONS_A1111 + COMFYUI_NODES +
                  AI_CONCEPTS + HARDWARE_PLATFORMS +
                  # Erweiterte Daten
                  EXTENDED_CHECKPOINTS_SD15 + EXTENDED_CHECKPOINTS_XL +
                  EXTENDED_LORAS + EXTENDED_EMBEDDINGS + EXTENDED_CONTROLNET +
                  COMFYUI_CUSTOM_NODES + PROMPT_TECHNIQUES + IMAGE_WORKFLOWS +
                  MODEL_PLATFORMS + IMAGE_FORMATS_TECH):
        add_node(entry[0], entry[1], entry[2], entry[3])

    # ── Organisationen → BaseModels ───────────────────────────────────────────
    org_model_map = {
        "org_stability_ai": ["bm_sd14","bm_sd15","bm_sd20","bm_sd21","bm_sdxl_base",
                             "bm_sdxl_refiner","bm_sdxl_turbo","bm_svd_xt","bm_sd3",
                             "bm_sd35_medium","bm_sd35_large","bm_animatediff",
                             "bm_deepfloyd_if"],
        "org_black_forest_labs": ["bm_flux1_dev","bm_flux1_schnell","bm_flux1_pro",
                                  "bm_flux_kontext","bm_flux2"],
        "org_tencent": ["bm_hunyuan_dit","bm_hunyuan_video"],
        "org_thudm": ["bm_cogvideox_2b","bm_cogvideox_5b"],
        "org_lightricks": ["bm_ltxv"],
        "org_wan_team": ["bm_wan_t2v","bm_wan_i2v"],
        "org_google": ["bm_pixart_alpha","bm_pixart_sigma"],
        "org_sber": ["bm_kandinsky_21","bm_kandinsky_22","bm_kandinsky_3"],
        "org_segmindai": ["bm_würstchen_v2","bm_würstchen_v3"],
        "org_bytedance": ["bm_sdxl_lightning"],
        "org_playgroundai": ["bm_playground_v2","bm_playground_v25"],
        "org_noobai": ["bm_noobai_xl"],
        "org_illustrious_team": ["bm_illustrious"],
        "org_pony_diffusion": ["bm_pony","bm_pony_v7"],
    }
    for org, models in org_model_map.items():
        for m in models:
            add_edge(org, m, "CREATED", 2.0)

    # ── Architekturen → BaseModels ────────────────────────────────────────────
    arch_model_map = {
        "arch_unet": ["bm_sd14","bm_sd15","bm_sd15_lcm","bm_sd20","bm_sd21",
                      "bm_sdxl_base","bm_sdxl_refiner","bm_sdxl_turbo",
                      "bm_playground_v2","bm_playground_v25","bm_kandinsky_21",
                      "bm_kandinsky_22","bm_noobai_xl","bm_illustrious"],
        "arch_dit": ["bm_pixart_alpha","bm_pixart_sigma","bm_auraflow"],
        "arch_mmdit": ["bm_sd3","bm_sd35_medium","bm_sd35_large","bm_flux1_dev",
                       "bm_flux1_schnell","bm_flux1_pro"],
        "arch_flow_matching": ["bm_flux1_dev","bm_flux1_schnell","bm_flux1_pro",
                               "bm_flux_kontext","bm_auraflow"],
        "arch_wan": ["bm_wan_t2v","bm_wan_i2v"],
        "arch_ltxv": ["bm_ltxv"],
        "arch_cogvideox": ["bm_cogvideox_2b","bm_cogvideox_5b"],
        "arch_hunyuan_video": ["bm_hunyuan_video"],
        "arch_svd": ["bm_svd_xt"],
        "arch_animate_diff": ["bm_animatediff","bm_animatediff_xl"],
        "arch_kandinsky": ["bm_kandinsky_21","bm_kandinsky_22"],
        "arch_würstchen": ["bm_würstchen_v2","bm_würstchen_v3"],
        "arch_lcm": ["bm_sd15_lcm","bm_sdxl_lcm"],
        "arch_turbo": ["bm_sdxl_turbo","bm_sdxl_lightning","bm_sdxl_hyper",
                       "bm_sd15_turbo","bm_sd15_hyper"],
        "arch_hidream": ["bm_hidream_i1"],
    }
    for arch, models in arch_model_map.items():
        for m in models:
            add_edge(arch, m, "USED_BY", 1.5)

    # ── Checkpoints → BaseModels ──────────────────────────────────────────────
    checkpoint_base_map = {
        "ckpt_dreamshaper8":    "bm_sd15",
        "ckpt_realistic_vision":"bm_sd15",
        "ckpt_deliberate_v6":   "bm_sd15",
        "ckpt_epicphotogasm":   "bm_sd15",
        "ckpt_chilloutmix":     "bm_sd15",
        "ckpt_aamxl_ultimate":  "bm_sd15",
        "ckpt_revanimated":     "bm_sd15",
        "ckpt_openjourney":     "bm_sd15",
        "ckpt_analog_diffusion":"bm_sd15",
        "ckpt_portrait_relax":  "bm_sd15",
        "ckpt_hassanblend":     "bm_sd15",
        "ckpt_elldreth_sd":     "bm_sd15",
        "ckpt_f222":            "bm_sd15",
        "ckpt_classicanim":     "bm_sd15",
        "ckpt_meina_v11":       "bm_sd15",
        "ckpt_juggernaut_xl":   "bm_sdxl_base",
        "ckpt_dreamshaper_xl":  "bm_sdxl_base",
        "ckpt_realvis_xl":      "bm_sdxl_base",
        "ckpt_nightvision_xl":  "bm_sdxl_base",
        "ckpt_epicrealism_xl":  "bm_sdxl_base",
        "ckpt_crystal_clear":   "bm_sdxl_base",
        "ckpt_animagine_xl3":   "bm_sdxl_base",
        "ckpt_kohaku_xl":       "bm_sdxl_base",
        "ckpt_counterfeit_xl":  "bm_sdxl_base",
        "ckpt_hassakuxl":       "bm_sdxl_base",
        "ckpt_pdxl":            "bm_pony",
        "ckpt_autismmix_pony":  "bm_pony",
        "ckpt_fluffydream":     "bm_pony",
        "ckpt_flux_realism":    "bm_flux1_dev",
        "ckpt_flux_anime":      "bm_flux1_dev",
        "ckpt_flux_portrait":   "bm_flux1_dev",
        "ckpt_sd3_medium":      "bm_sd3",
    }
    for ckpt, base in checkpoint_base_map.items():
        add_edge(ckpt, base, "FINETUNED_FROM", 1.8)
        add_node_type_edge = (ckpt, "mt_checkpoint", "IS_TYPE", 1.0)
        edges.append({"source": ckpt, "target": "mt_checkpoint",
                       "relation": "IS_TYPE", "weight": 1.0})

    # ── WebUIs → unterstützte ModelTypes ─────────────────────────────────────
    webui_type_support = {
        "ui_a1111": ["mt_checkpoint","mt_lora","mt_lycoris","mt_embedding",
                     "mt_hypernetwork","mt_controlnet","mt_vae","mt_upscaler"],
        "ui_comfyui": ["mt_checkpoint","mt_lora","mt_controlnet","mt_vae",
                       "mt_text_encoder","mt_unet","mt_diffuser","mt_clip_model",
                       "mt_ipadapter","mt_upscaler","mt_style_model","mt_gligen",
                       "mt_motion_module","mt_embedding"],
        "ui_forge": ["mt_checkpoint","mt_lora","mt_lycoris","mt_controlnet",
                     "mt_vae","mt_ipadapter","mt_t2i_adapter","mt_embedding","mt_upscaler"],
        "ui_reforge": ["mt_checkpoint","mt_lora","mt_controlnet","mt_vae","mt_embedding"],
        "ui_sdnext": ["mt_checkpoint","mt_lora","mt_diffuser","mt_controlnet",
                      "mt_vae","mt_ipadapter","mt_embedding"],
        "ui_fooocus": ["mt_checkpoint","mt_lora","mt_controlnet","mt_vae",
                       "mt_embedding","mt_upscaler"],
        "ui_invokeai": ["mt_checkpoint","mt_diffuser","mt_lora","mt_controlnet",
                        "mt_vae","mt_ipadapter","mt_embedding"],
        "ui_swarmui": ["mt_checkpoint","mt_lora","mt_controlnet","mt_vae"],
        "ui_kohya": ["mt_lora","mt_lycoris","mt_dora","mt_checkpoint"],
        "ui_onetrainer": ["mt_lora","mt_checkpoint","mt_embedding"],
        "ui_fluxgym": ["mt_lora"],
    }
    for ui, types in webui_type_support.items():
        for t in types:
            add_edge(ui, t, "SUPPORTS", 1.0)

    # ── WebUIs → BaseModels (Kompatibilität) ──────────────────────────────────
    ui_base_compat = {
        "ui_a1111": ["bm_sd14","bm_sd15","bm_sd15_lcm","bm_sd20","bm_sd21"],
        "ui_forge": ["bm_sd14","bm_sd15","bm_sdxl_base","bm_flux1_dev",
                     "bm_flux1_schnell","bm_sd3","bm_sd35_medium"],
        "ui_comfyui": ["bm_sd14","bm_sd15","bm_sdxl_base","bm_flux1_dev",
                       "bm_flux1_schnell","bm_sd3","bm_sd35_medium","bm_svd_xt",
                       "bm_animatediff","bm_wan_t2v","bm_wan_i2v","bm_ltxv",
                       "bm_cogvideox_5b","bm_hunyuan_video","bm_hidream_i1"],
        "ui_sdnext": ["bm_sd15","bm_sdxl_base","bm_flux1_dev","bm_sd3"],
        "ui_fooocus": ["bm_sdxl_base","bm_sdxl_refiner","bm_pony"],
        "ui_invokeai": ["bm_sd15","bm_sdxl_base","bm_flux1_dev","bm_sd3"],
        "ui_swarmui": ["bm_sd15","bm_sdxl_base","bm_flux1_dev","bm_sd3"],
        "ui_kohya": ["bm_sd15","bm_sdxl_base","bm_flux1_dev"],
        "ui_fluxgym": ["bm_flux1_dev","bm_flux1_schnell"],
    }
    for ui, bases in ui_base_compat.items():
        for b in bases:
            add_edge(ui, b, "COMPATIBLE_WITH", 1.0)

    # ── StabilityMatrix → WebUIs ──────────────────────────────────────────────
    for ui_id, _, utype, _ in WEBUIS:
        if ui_id != "ui_stability_matrix":
            add_edge("ui_stability_matrix", ui_id, "MANAGES", 1.5)

    # ── ControlNet Modelle → BaseModels ───────────────────────────────────────
    for cn_id, _, _, _ in CONTROLNET_MODELS:
        if "xl" in cn_id or "flux" in cn_id:
            base = "bm_flux1_dev" if "flux" in cn_id else "bm_sdxl_base"
        elif "union" in cn_id:
            base = "bm_sdxl_base"
        else:
            base = "bm_sd15"
        add_edge(cn_id, base, "TRAINED_ON", 1.5)
        add_edge(cn_id, "mt_controlnet" if "xl" not in cn_id else "mt_controlnet_xl",
                 "IS_TYPE", 1.0)

    # ── LoRA Modelle → ModelType + BaseModel ─────────────────────────────────
    for lora_id, _, _, _ in LORA_STYLES:
        add_edge(lora_id, "mt_lora", "IS_TYPE", 1.0)
        base = "bm_flux1_dev" if "flux" in lora_id else (
               "bm_sdxl_base" if "xl" in lora_id else "bm_sd15")
        add_edge(lora_id, base, "TRAINED_ON", 1.2)

    # ── Embeddings → ModelType ────────────────────────────────────────────────
    for emb_id, _, _, _ in EMBEDDINGS:
        add_edge(emb_id, "mt_embedding", "IS_TYPE", 1.0)
        add_edge(emb_id, "bm_sd15", "TRAINED_ON", 1.0)

    # ── Upscaler → ModelType ──────────────────────────────────────────────────
    for up_id, _, _, _ in UPSCALERS:
        add_edge(up_id, "mt_upscaler", "IS_TYPE", 1.0)

    # ── Architectures → Concepts ──────────────────────────────────────────────
    add_edge("arch_unet", "concept_diffusion", "IMPLEMENTS", 1.0)
    add_edge("arch_dit", "concept_diffusion", "IMPLEMENTS", 1.0)
    add_edge("arch_mmdit", "concept_diffusion", "IMPLEMENTS", 1.0)
    add_edge("arch_lora", "concept_diffusion", "MODIFIES", 0.8)
    add_edge("arch_controlnet", "concept_diffusion", "MODIFIES", 1.0)
    add_edge("arch_vae", "concept_latent_space", "ENCODES", 1.5)
    add_edge("arch_clip", "concept_attention", "USES", 1.0)

    # ── Extensions → WebUI ───────────────────────────────────────────────────
    for ext_id, _, _, _ in EXTENSIONS_A1111:
        add_edge("ui_a1111", ext_id, "HAS_EXTENSION", 1.0)
        add_edge("ui_forge", ext_id, "HAS_EXTENSION", 0.8)

    # ── ComfyUI Nodes → ComfyUI ──────────────────────────────────────────────
    for node_id, _, _, _ in COMFYUI_NODES:
        add_edge("ui_comfyui", node_id, "HAS_NODE", 1.0)

    # ── Datasets → Organisationen (genutzt für Training) ─────────────────────
    dataset_org_map = {
        "ds_laion_5b": ["org_stability_ai","org_stability_ai"],
        "ds_danbooru": ["org_noobai","org_illustrious_team","org_pony_diffusion"],
        "ds_e621": ["org_pony_diffusion"],
        "ds_laion_aesthetics": ["org_stability_ai","org_playgroundai"],
        "ds_webvid10m": ["org_wan_team","org_lightricks"],
    }
    for ds, orgs in dataset_org_map.items():
        for org in set(orgs):
            add_edge(org, ds, "TRAINED_ON", 1.5)

    # ── Hardware → Konzepte ───────────────────────────────────────────────────
    add_edge("hw_cuda", "concept_flash_attn", "ENABLES", 1.0)
    add_edge("hw_cuda", "concept_xformers", "ENABLES", 1.0)
    add_edge("hw_tensorrt", "concept_quantization", "USES", 1.0)
    add_edge("hw_rocm", "hw_amd_rx7900xtx", "RUNS_ON", 1.0)
    add_edge("hw_directml", "hw_intel_arc_a770", "RUNS_ON", 1.0)
    add_edge("hw_metal", "hw_apple_m3max", "RUNS_ON", 1.0)

    # ── Erweiterte Checkpoints → BaseModels ──────────────────────────────────
    for ckpt_id, _, _, _ in EXTENDED_CHECKPOINTS_SD15:
        add_edge(ckpt_id, "bm_sd15", "FINETUNED_FROM", 1.5)
        edges.append({"source": ckpt_id, "target": "mt_checkpoint", "relation": "IS_TYPE", "weight": 1.0})
    for ckpt_id, _, _, _ in EXTENDED_CHECKPOINTS_XL:
        base = "bm_pony" if "pony" in ckpt_id or "Pony" in ckpt_id else "bm_sdxl_base"
        add_edge(ckpt_id, base, "FINETUNED_FROM", 1.5)
        edges.append({"source": ckpt_id, "target": "mt_checkpoint", "relation": "IS_TYPE", "weight": 1.0})

    # ── Erweiterte LoRAs → ModelType + BaseModel ──────────────────────────────
    for lora_id, _, _, _ in EXTENDED_LORAS:
        add_edge(lora_id, "mt_lora", "IS_TYPE", 1.0)
        base = "bm_flux1_dev" if "flux" in lora_id else (
               "bm_sdxl_base" if "xl" in lora_id else "bm_sd15")
        add_edge(lora_id, base, "TRAINED_ON", 1.2)

    # ── Erweiterte Embeddings ─────────────────────────────────────────────────
    for emb_id, _, _, _ in EXTENDED_EMBEDDINGS:
        add_edge(emb_id, "mt_embedding", "IS_TYPE", 1.0)
        base = "bm_sdxl_base" if "score" in emb_id or "source" in emb_id else "bm_sd15"
        add_edge(emb_id, base, "TRAINED_ON", 1.0)

    # ── Erweiterte ControlNet → BaseModels ───────────────────────────────────
    for cn_id, _, _, _ in EXTENDED_CONTROLNET:
        if "flux" in cn_id:
            add_edge(cn_id, "bm_flux1_dev", "TRAINED_ON", 1.5)
        elif "sd3" in cn_id:
            add_edge(cn_id, "bm_sd3", "TRAINED_ON", 1.5)
        elif "xl" in cn_id:
            add_edge(cn_id, "bm_sdxl_base", "TRAINED_ON", 1.5)
            edges.append({"source": cn_id, "target": "mt_controlnet_xl", "relation": "IS_TYPE", "weight": 1.0})
        else:
            add_edge(cn_id, "bm_sd15", "TRAINED_ON", 1.5)
            edges.append({"source": cn_id, "target": "mt_controlnet", "relation": "IS_TYPE", "weight": 1.0})

    # ── Custom Node Packs → ComfyUI ───────────────────────────────────────────
    for pack_id, _, _, _ in COMFYUI_CUSTOM_NODES:
        add_edge("ui_comfyui", pack_id, "HAS_EXTENSION", 1.0)

    # ── Prompt Techniken → Konzepte ───────────────────────────────────────────
    for pt_id, _, _, _ in PROMPT_TECHNIQUES:
        add_edge(pt_id, "concept_prompt", "EXTENDS", 1.0)
    for pt_id in ["pt_attention_syntax","pt_emphasis","pt_de_emphasis","pt_andcondition"]:
        add_edge(pt_id, "concept_cfgscale", "INTERACTS_WITH", 0.8)

    # ── Workflows → WebUIs ────────────────────────────────────────────────────
    comfyui_workflows = ["wf_controlnet_chain","wf_ipadapter","wf_flux_standard",
                         "wf_flux_ip_adapter","wf_flux_redux","wf_flux_kontext",
                         "wf_animatediff","wf_wan_t2v","wf_wan_i2v","wf_ltxv_workflow",
                         "wf_cogvideo_workflow","wf_sam_segmentation","wf_layerdiffuse",
                         "wf_ic_light","wf_pulid_consistency","wf_regional_prompt",
                         "wf_batch_generate"]
    a1111_workflows = ["wf_txt2img_basic","wf_img2img_basic","wf_inpainting_basic",
                       "wf_outpainting","wf_hires_fix","wf_adetailer_auto"]
    for wf in comfyui_workflows:
        if wf in nodes:
            add_edge("ui_comfyui", wf, "RUNS_WORKFLOW", 1.0)
    for wf in a1111_workflows:
        if wf in nodes:
            add_edge("ui_a1111", wf, "RUNS_WORKFLOW", 1.0)
            add_edge("ui_forge", wf, "RUNS_WORKFLOW", 0.9)

    # Alle Workflows → Concept Txt2Img oder Img2Img
    for wf_id, _, _, _ in IMAGE_WORKFLOWS:
        concept = "concept_txt2img" if "txt" in wf_id or "generat" in wf_id else "concept_img2img"
        add_edge(wf_id, concept, "USES_TECHNIQUE", 0.8)

    # ── Plattformen → Organisationen ─────────────────────────────────────────
    add_edge("plat_civitai", "org_civitai", "OPERATED_BY", 2.0)
    add_edge("plat_huggingface", "org_huggingface", "OPERATED_BY", 2.0)
    add_edge("plat_dreamstudio", "org_stability_ai", "OPERATED_BY", 1.5)
    add_edge("plat_clipdrop", "org_stability_ai", "OPERATED_BY", 1.5)
    add_edge("plat_novelai", "org_stability_ai", "USES_MODELS_OF", 1.0)
    add_edge("plat_leonardo", "org_stability_ai", "BUILT_ON", 1.0)

    # Plattformen hosten Modelle
    for org_id in ["org_stability_ai","org_black_forest_labs","org_tencent",
                   "org_meta","org_google"]:
        add_edge("plat_huggingface", org_id, "HOSTS_MODELS_OF", 1.0)
        add_edge("plat_civitai", org_id, "HOSTS_MODELS_OF", 0.8)

    # ── Datei-Formate → Modelltypen ───────────────────────────────────────────
    add_edge("fmt_safetensors", "mt_checkpoint", "STORES", 1.5)
    add_edge("fmt_safetensors", "mt_lora", "STORES", 1.5)
    add_edge("fmt_ckpt", "mt_checkpoint", "STORES", 1.0)
    add_edge("fmt_diffusers_dir", "mt_diffuser", "STORES", 1.5)
    add_edge("fmt_workflow_json", "mt_workflow", "STORES", 1.5)
    add_edge("fmt_gguf", "concept_quantization", "ENABLES", 1.0)
    add_edge("fmt_onnx", "concept_quantization", "ENABLES", 1.0)

    # ── Plattformen → Modelltypen ─────────────────────────────────────────────
    for fmt_type in ["mt_checkpoint","mt_lora","mt_embedding","mt_controlnet"]:
        add_edge("plat_civitai", fmt_type, "DISTRIBUTES", 1.0)
        add_edge("plat_huggingface", fmt_type, "DISTRIBUTES", 1.0)

    # ── Samplers → Concepts ───────────────────────────────────────────────────
    for samp_id, _, _, _ in SAMPLERS:
        add_edge(samp_id, "concept_diffusion", "SAMPLES_FROM", 0.8)
    for sched_id, _, _, _ in SCHEDULERS:
        add_edge(sched_id, "concept_diffusion", "SCHEDULES", 0.8)

    # ── Training Frameworks → BaseModels ─────────────────────────────────────
    tf_base_map = {
        "tf_kohya_scripts": ["bm_sd15","bm_sdxl_base","bm_flux1_dev"],
        "tf_fluxgym": ["bm_flux1_dev","bm_flux1_schnell"],
        "tf_ai_toolkit": ["bm_flux1_dev"],
        "tf_x_flux": ["bm_flux1_dev","bm_flux1_schnell"],
        "tf_simpleTuner": ["bm_sdxl_base","bm_flux1_dev","bm_sd3"],
        "tf_onetrainer": ["bm_sd15","bm_sdxl_base","bm_flux1_dev"],
    }
    for tf, bases in tf_base_map.items():
        for b in bases:
            if tf in nodes:
                add_edge(tf, b, "TRAINS", 1.2)

    # ── Base Model Varianten ──────────────────────────────────────────────────
    variant_of = [
        ("bm_sd15_lcm", "bm_sd15"),
        ("bm_sd15_turbo", "bm_sd15"),
        ("bm_sd15_hyper", "bm_sd15"),
        ("bm_sd21_unclip", "bm_sd21"),
        ("bm_sdxl_refiner", "bm_sdxl_base"),
        ("bm_sdxl_turbo", "bm_sdxl_base"),
        ("bm_sdxl_lightning", "bm_sdxl_base"),
        ("bm_sdxl_hyper", "bm_sdxl_base"),
        ("bm_sdxl_lcm", "bm_sdxl_base"),
        ("bm_flux1_schnell", "bm_flux1_dev"),
        ("bm_flux1_pro", "bm_flux1_dev"),
        ("bm_flux_kontext", "bm_flux1_dev"),
        ("bm_flux_krea", "bm_flux1_dev"),
        ("bm_flux2", "bm_flux1_dev"),
        ("bm_sd35_medium", "bm_sd3"),
        ("bm_sd35_large", "bm_sd3"),
        ("bm_cogvideox_5b", "bm_cogvideox_2b"),
        ("bm_animatediff_xl", "bm_animatediff"),
        ("bm_kandinsky_22", "bm_kandinsky_21"),
        ("bm_kandinsky_3", "bm_kandinsky_22"),
        ("bm_würstchen_v3", "bm_würstchen_v2"),
        ("bm_pixart_sigma", "bm_pixart_alpha"),
        ("bm_pony_v7", "bm_pony"),
        ("bm_noobai_xl", "bm_sdxl_base"),
        ("bm_illustrious", "bm_sdxl_base"),
        ("bm_anything_v5", "bm_anything_v3"),
        ("bm_anything_v3", "bm_sd15"),
    ]
    for child, parent in variant_of:
        add_edge(child, parent, "IS_VARIANT_OF", 2.0)

    # ── Organsation → Organisation (Investition/Kooperation) ─────────────────
    add_edge("org_stability_ai", "org_laion", "PARTNERED_WITH", 1.5)
    add_edge("org_huggingface", "org_stability_ai", "HOSTS_MODELS_OF", 1.2)
    add_edge("org_civitai", "org_stability_ai", "DISTRIBUTES_FOR", 1.0)

    # ── Konzept-Verkettungen ──────────────────────────────────────────────────
    add_edge("concept_diffusion", "concept_latent_space", "OPERATES_IN", 1.5)
    add_edge("concept_latent_space", "concept_vram_opt", "REQUIRES", 1.0)
    add_edge("concept_cfg_rescale", "concept_cfgscale", "MODIFIES", 1.0)
    add_edge("concept_quantization", "concept_vram_opt", "ACHIEVES", 1.2)
    add_edge("concept_distillation", "concept_lcm_sampling", "ENABLES", 1.5)

    return nodes, edges


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT FUNKTIONEN
# ─────────────────────────────────────────────────────────────────────────────

def export_neo4j(nodes, edges, out_dir):
    """Exportiert als Neo4j-kompatibles CSV + Cypher Schema"""
    os.makedirs(out_dir, exist_ok=True)

    # nodes.csv
    with open(os.path.join(out_dir, "nodes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["nodeId:ID", ":LABEL", "label", "type", "description"])
        w.writeheader()
        for nid, n in nodes.items():
            w.writerow({
                "nodeId:ID": nid,
                ":LABEL": n["type"],
                "label": n["label"],
                "type": n["type"],
                "description": n.get("description", "")
            })

    # edges.csv
    with open(os.path.join(out_dir, "edges.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[":START_ID", ":END_ID", ":TYPE", "weight:double"])
        w.writeheader()
        for e in edges:
            w.writerow({
                ":START_ID": e["source"],
                ":END_ID": e["target"],
                ":TYPE": e["relation"],
                "weight:double": e["weight"]
            })

    # schema.cypher
    cypher_lines = [
        "// AI Universe Map – Neo4j Cypher Import Schema",
        f"// Generiert: {datetime.now().isoformat()}",
        f"// Knoten: {len(nodes)} | Kanten: {len(edges)}",
        "",
        "// ── Constraints ───────────────────────────────────────",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.nodeId IS UNIQUE;",
        "",
        "// ── Beispiel-Abfragen ─────────────────────────────────",
        "// Alle Modelle eines BaseModels finden:",
        "// MATCH (c:Checkpoint)-[:FINETUNED_FROM]->(b:BaseModel {label:'SD 1.5'}) RETURN c.label;",
        "",
        "// ControlNet Modelle für SDXL:",
        "// MATCH (cn:ControlNetModel)-[:TRAINED_ON]->(b:BaseModel {label:'SDXL 1.0 Base'}) RETURN cn;",
        "",
        "// Alle WebUIs die Flux unterstützen:",
        "// MATCH (ui:WebUI)-[:COMPATIBLE_WITH]->(b:BaseModel) WHERE b.label CONTAINS 'FLUX' RETURN ui.label;",
        "",
        "// ── Import-Befehl (neo4j-admin) ───────────────────────",
        "// neo4j-admin database import full --nodes=nodes.csv --relationships=edges.csv ai_universe",
        "",
        "// ── LOAD CSV Alternative ──────────────────────────────",
        "LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row",
        "CALL apoc.create.node([row[':LABEL']], {",
        "  nodeId: row['nodeId:ID'],",
        "  label: row.label,",
        "  type: row.type,",
        "  description: row.description",
        "}) YIELD node RETURN count(node);",
        "",
        "LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row",
        "MATCH (a {nodeId: row[':START_ID']}), (b {nodeId: row[':END_ID']})",
        "CALL apoc.create.relationship(a, row[':TYPE'], {weight: toFloat(row['weight:double'])}, b)",
        "YIELD rel RETURN count(rel);",
    ]
    with open(os.path.join(out_dir, "schema.cypher"), "w", encoding="utf-8") as f:
        f.write("\n".join(cypher_lines))

    print(f"[Neo4j] {len(nodes)} Knoten, {len(edges)} Kanten → {out_dir}/")


def export_gephi(nodes, edges, out_path):
    """Exportiert als GEXF für Gephi"""
    gexf = ET.Element("gexf", {
        "xmlns": "http://gexf.net/1.3",
        "xmlns:viz": "http://gexf.net/1.3/viz",
        "version": "1.3"
    })
    meta = ET.SubElement(gexf, "meta", lastmodifieddate=datetime.now().strftime("%Y-%m-%d"))
    ET.SubElement(meta, "creator").text = "AI Universe Map Generator"
    ET.SubElement(meta, "description").text = f"AI Universe Map – {len(nodes)} Knoten, {len(edges)} Kanten"

    graph = ET.SubElement(gexf, "graph", defaultedgetype="directed", mode="static")

    # Attributes
    node_attrs = ET.SubElement(graph, "attributes", attclass="node")
    ET.SubElement(node_attrs, "attribute", id="0", title="type", type="string")
    ET.SubElement(node_attrs, "attribute", id="1", title="description", type="string")

    edge_attrs = ET.SubElement(graph, "attributes", attclass="edge")
    ET.SubElement(edge_attrs, "attribute", id="0", title="relation", type="string")

    # Node type → color mapping
    type_colors = {
        "Organization": (255, 165, 0),
        "Architecture": (0, 150, 255),
        "BaseModel": (50, 205, 50),
        "ModelType": (255, 215, 0),
        "WebUI": (220, 20, 60),
        "TrainingFramework": (147, 112, 219),
        "Dataset": (64, 224, 208),
        "ControlNetModel": (255, 99, 71),
        "Upscaler": (144, 238, 144),
        "Checkpoint": (100, 149, 237),
        "LoRAModel": (255, 182, 193),
        "Embedding": (255, 160, 122),
        "Sampler": (176, 196, 222),
        "Scheduler": (152, 251, 152),
        "Extension": (255, 228, 196),
        "ComfyNode": (230, 230, 250),
        "Concept": (245, 245, 220),
        "Hardware": (192, 192, 192),
    }

    nodes_el = ET.SubElement(graph, "nodes")
    for nid, n in nodes.items():
        node_el = ET.SubElement(nodes_el, "node", id=nid, label=n["label"])
        attvals = ET.SubElement(node_el, "attvalues")
        ET.SubElement(attvals, "attvalue", **{"for": "0", "value": n["type"]})
        ET.SubElement(attvals, "attvalue", **{"for": "1", "value": n.get("description","")})
        # Farbe
        r, g, b = type_colors.get(n["type"], (200, 200, 200))
        ET.SubElement(node_el, "viz:color", r=str(r), g=str(g), b=str(b), a="1.0")
        ET.SubElement(node_el, "viz:size", value="10")

    edges_el = ET.SubElement(graph, "edges")
    for i, e in enumerate(edges):
        edge_el = ET.SubElement(edges_el, "edge",
                                id=str(i),
                                source=e["source"],
                                target=e["target"],
                                weight=str(e["weight"]))
        attvals = ET.SubElement(edge_el, "attvalues")
        ET.SubElement(attvals, "attvalue", **{"for": "0", "value": e["relation"]})

    # Pretty print
    xml_str = minidom.parseString(ET.tostring(gexf, encoding="unicode")).toprettyxml(indent="  ")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"[Gephi] {len(nodes)} Knoten, {len(edges)} Kanten → {out_path}")


def export_obsidian(nodes, edges, out_dir):
    """Exportiert als Obsidian Vault (Markdown mit Wikilinks)"""
    os.makedirs(out_dir, exist_ok=True)

    # Index erstellen
    type_groups = {}
    for nid, n in nodes.items():
        type_groups.setdefault(n["type"], []).append(n)

    # Adjazenzliste erstellen
    outgoing = {}  # nid -> [(target_nid, relation)]
    incoming = {}  # nid -> [(source_nid, relation)]
    for e in edges:
        outgoing.setdefault(e["source"], []).append((e["target"], e["relation"]))
        incoming.setdefault(e["target"], []).append((e["source"], e["relation"]))

    safe_name = lambda s: re.sub(r'[\\/:*?"<>|]', '_', s)

    for nid, n in nodes.items():
        fname = safe_name(n["label"]) + ".md"
        lines = [
            f"# {n['label']}",
            "",
            f"**Typ:** `{n['type']}`",
        ]
        if n.get("description"):
            lines += ["", n["description"]]

        # Tags
        lines += ["", f"#AI/{n['type']}"]

        # Ausgehende Links
        out_rels = outgoing.get(nid, [])
        if out_rels:
            lines += ["", "## Verbindungen (ausgehend)", ""]
            rel_groups = {}
            for tgt, rel in out_rels:
                rel_groups.setdefault(rel, []).append(tgt)
            for rel, targets in sorted(rel_groups.items()):
                lines.append(f"**{rel}**")
                for t in targets:
                    t_label = nodes[t]["label"] if t in nodes else t
                    lines.append(f"- [[{safe_name(t_label)}]]")
                lines.append("")

        # Eingehende Links
        in_rels = incoming.get(nid, [])
        if in_rels:
            lines += ["## Verbindungen (eingehend)", ""]
            rel_groups = {}
            for src, rel in in_rels:
                rel_groups.setdefault(rel, []).append(src)
            for rel, sources in sorted(rel_groups.items()):
                lines.append(f"**{rel}**")
                for s in sources:
                    s_label = nodes[s]["label"] if s in nodes else s
                    lines.append(f"- [[{safe_name(s_label)}]]")
                lines.append("")

        filepath = os.path.join(out_dir, fname)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # _INDEX.md
    index_lines = ["# AI Universe Map – Index", ""]
    for ntype, group in sorted(type_groups.items()):
        index_lines.append(f"## {ntype} ({len(group)})")
        for n in sorted(group, key=lambda x: x["label"]):
            index_lines.append(f"- [[{safe_name(n['label'])}]]")
        index_lines.append("")

    with open(os.path.join(out_dir, "_INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    print(f"[Obsidian] {len(nodes)} Dateien → {out_dir}/")


def export_graphviz(nodes, edges, out_path):
    """Exportiert als Graphviz DOT Datei"""
    type_colors = {
        "Organization": "#FFA500",
        "Architecture": "#0096FF",
        "BaseModel": "#32CD32",
        "ModelType": "#FFD700",
        "WebUI": "#DC143C",
        "TrainingFramework": "#9370DB",
        "Dataset": "#40E0D0",
        "ControlNetModel": "#FF6347",
        "Upscaler": "#90EE90",
        "Checkpoint": "#6495ED",
        "LoRAModel": "#FFB6C1",
        "Embedding": "#FFA07A",
        "Sampler": "#B0C4DE",
        "Scheduler": "#98FB98",
        "Extension": "#FFE4C4",
        "ComfyNode": "#E6E6FA",
        "Concept": "#F5F5DC",
        "Hardware": "#C0C0C0",
    }

    lines = [
        "// AI Universe Map",
        f"// Generiert: {datetime.now().isoformat()}",
        f"// Knoten: {len(nodes)} | Kanten: {len(edges)}",
        "digraph AI_Universe {",
        "  graph [rankdir=LR, overlap=false, splines=true, fontname=\"Arial\"];",
        "  node [shape=box, style=\"filled,rounded\", fontname=\"Arial\", fontsize=9];",
        "  edge [fontname=\"Arial\", fontsize=7];",
        "",
        "  // ── Cluster-Definitionen ────────────────────────────────",
    ]

    # Nach Typ gruppieren
    type_groups = {}
    for nid, n in nodes.items():
        type_groups.setdefault(n["type"], []).append(nid)

    for ntype, nids in sorted(type_groups.items()):
        color = type_colors.get(ntype, "#EEEEEE")
        lines.append(f"  subgraph cluster_{ntype} {{")
        lines.append(f"    label=\"{ntype}\";")
        lines.append(f"    style=filled; fillcolor=\"{color}22\";")
        lines.append(f"    color=\"{color}\";")
        for nid in nids:
            n = nodes[nid]
            label = n["label"].replace('"', '\\"')
            fill = color
            lines.append(f'    "{nid}" [label="{label}", fillcolor="{fill}", tooltip="{n.get("description","")[:60]}"];')
        lines.append("  }")
        lines.append("")

    # Kanten
    lines.append("  // ── Kanten ──────────────────────────────────────────────")
    rel_colors = {
        "CREATED": "#FF4500",
        "IS_VARIANT_OF": "#1E90FF",
        "FINETUNED_FROM": "#32CD32",
        "COMPATIBLE_WITH": "#9370DB",
        "SUPPORTS": "#FF8C00",
        "TRAINS": "#DC143C",
        "TRAINED_ON": "#20B2AA",
        "IS_TYPE": "#808080",
        "MANAGES": "#FF69B4",
        "HAS_EXTENSION": "#DDA0DD",
        "HAS_NODE": "#B0C4DE",
    }
    for e in edges:
        color = rel_colors.get(e["relation"], "#999999")
        rel = e["relation"].replace('"', '\\"')
        lines.append(f'  "{e["source"]}" -> "{e["target"]}" [label="{rel}", color="{color}", penwidth={e["weight"]}];')

    lines.append("}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[Graphviz] {len(nodes)} Knoten, {len(edges)} Kanten → {out_path}")


def export_stats(nodes, edges, out_path):
    """Statistik-Zusammenfassung"""
    type_count = {}
    for n in nodes.values():
        type_count[n["type"]] = type_count.get(n["type"], 0) + 1

    rel_count = {}
    for e in edges:
        rel_count[e["relation"]] = rel_count.get(e["relation"], 0) + 1

    lines = [
        "# AI Universe Map – Statistik",
        f"Generiert: {datetime.now().isoformat()}",
        "",
        f"## Gesamt: {len(nodes)} Knoten, {len(edges)} Kanten",
        "",
        "## Knoten nach Typ",
    ]
    for t, c in sorted(type_count.items(), key=lambda x: -x[1]):
        lines.append(f"  {t:<25} {c:>4}")

    lines += ["", "## Beziehungstypen"]
    for r, c in sorted(rel_count.items(), key=lambda x: -x[1]):
        lines.append(f"  {r:<30} {c:>4}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Auch auf Console
    print("\n" + "\n".join(lines[:30]))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Universe Map Generator")
    parser.add_argument("--format", default="all",
                        choices=["all", "neo4j", "gephi", "obsidian", "graphviz"],
                        help="Exportformat(e)")
    parser.add_argument("--out", default="output", help="Ausgabeverzeichnis")
    args = parser.parse_args()

    print(f"[*] Baue AI Universe Graph...")
    nodes, edges = build_graph()
    print(f"[*] {len(nodes)} Knoten, {len(edges)} Kanten erstellt.")

    out = args.out
    os.makedirs(out, exist_ok=True)

    fmt = args.format
    if fmt in ("all", "neo4j"):
        export_neo4j(nodes, edges, os.path.join(out, "neo4j"))
    if fmt in ("all", "gephi"):
        export_gephi(nodes, edges, os.path.join(out, "ai_universe.gexf"))
    if fmt in ("all", "obsidian"):
        export_obsidian(nodes, edges, os.path.join(out, "obsidian"))
    if fmt in ("all", "graphviz"):
        export_graphviz(nodes, edges, os.path.join(out, "ai_universe.dot"))

    export_stats(nodes, edges, os.path.join(out, "STATS.txt"))

    print(f"\n[✓] Fertig! Alle Exports in: {os.path.abspath(out)}/")
    print(f"    neo4j/    → Neo4j Import CSV + Cypher")
    print(f"    *.gexf    → Gephi öffnen")
    print(f"    obsidian/ → Als Vault in Obsidian öffnen")
    print(f"    *.dot     → dot -Tsvg ai_universe.dot -o map.svg")


if __name__ == "__main__":
    main()
