# backend-ml/app/vision/embedding.py
import numpy as np
import open_clip
import torch
from pathlib import Path
from PIL import Image

EMBEDDING_DIM = 768
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLIP_ONNX_PATH = Path(__file__).resolve().parent.parent.parent / "models/bioclip.onnx"

# Try to use ONNX Runtime first, fallback to PyTorch
try:
    import onnxruntime as ort
    USE_ONNX = True
    print("Using ONNX Runtime for CLIP embeddings")
    
    # Export CLIP model to ONNX if it doesn't exist
    if not CLIP_ONNX_PATH.exists():
        print("Exporting BioCLIP model to ONNX...")
        clip_model, _, clip_preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
        clip_model = clip_model.to('cpu').eval()
        
        # Create dummy input
        dummy_image = Image.new('RGB', (224, 224))
        dummy_input = clip_preprocess(dummy_image).unsqueeze(0)
        
        # Export to ONNX
        torch.onnx.export(
            clip_model.visual,
            dummy_input,
            str(CLIP_ONNX_PATH),
            input_names=['image'],
            output_names=['embedding'],
            dynamic_axes={'image': {0: 'batch_size'}},
            opset_version=14
        )
        print(f"CLIP model exported to {CLIP_ONNX_PATH}")
    
    # Load ONNX session
    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    clip_session = ort.InferenceSession(
        str(CLIP_ONNX_PATH),
        sess_options,
        providers=['CPUExecutionProvider']
    )
    
    # Load preprocessing only
    _, _, clip_preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
    clip_model = None
    
except ImportError:
    print("ONNX Runtime not available, using PyTorch")
    USE_ONNX = False
    clip_model, _, clip_preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
    tokenizer = open_clip.get_tokenizer('hf-hub:imageomics/bioclip-2')
    clip_model = clip_model.to(DEVICE).eval()
    clip_session = None


def embed(image):
    """
    Generate embedding for an image.
    Uses ONNX Runtime if available, otherwise PyTorch.
    
    Args:
        image: PIL Image
        
    Returns:
        numpy array of shape (768,)
    """
    if USE_ONNX:
        # ONNX inference
        tensor = clip_preprocess(image).unsqueeze(0).numpy()
        input_name = clip_session.get_inputs()[0].name
        feat = clip_session.run(None, {input_name: tensor})[0]
        
        # Normalize
        feat = feat / np.linalg.norm(feat, axis=-1, keepdims=True)
        return feat.squeeze(0)
    else:
        # PyTorch inference (original)
        with torch.no_grad():
            tensor = clip_preprocess(image).unsqueeze(0).to(DEVICE)
            feat = clip_model.encode_image(tensor)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.squeeze(0).cpu().numpy()
