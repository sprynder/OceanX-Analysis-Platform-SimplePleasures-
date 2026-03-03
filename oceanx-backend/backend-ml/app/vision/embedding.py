# backend-ml/app/vision/embedding.py
import numpy as np
import open_clip
import timm
import torch
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from threading import Lock

EMBEDDING_DIM = 768
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model_lock = Lock()
_current_model_name = None
_current_model = None
_current_preprocess = None


def _load_model(model_name: str) -> None:
    global _current_model_name, _current_model, _current_preprocess

    if model_name not in {"bioclip2", "dinov3"}:
        raise ValueError(f"Unknown embedding model: {model_name}")

    with _model_lock:
        if _current_model_name == model_name and _current_model is not None:
            return

        # Unload previous model to free memory
        if _current_model is not None:
            del _current_model
            _current_model = None
            _current_preprocess = None
            _current_model_name = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if model_name == "bioclip2":
            model, _, preprocess = open_clip.create_model_and_transforms(
                "hf-hub:imageomics/bioclip-2"
            )
            _current_model = model.to(DEVICE).eval()
            _current_preprocess = preprocess
            _current_model_name = "bioclip2"
            return

        model = timm.create_model(
            "vit_base_patch16_dinov3_qkvb.lvd1689m",
            pretrained=True,
            num_classes=0,
        )
        model = model.to(DEVICE).eval()
        config = resolve_data_config({}, model=model)
        preprocess = create_transform(**config)
        _current_model = model
        _current_preprocess = preprocess
        _current_model_name = "dinov3"


def embed(image, model_name: str = "bioclip2"):
    _load_model(model_name)
    with torch.no_grad():
        tensor = _current_preprocess(image).unsqueeze(0).to(DEVICE)
        if _current_model_name == "bioclip2":
            feat = _current_model.encode_image(tensor)
        else:
            feat = _current_model.forward_features(tensor)
            # ViT-style outputs [B, tokens, C] or [B, C]
            if feat.dim() == 3:
                feat = feat[:, 0, :]
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.squeeze(0).cpu().numpy()
