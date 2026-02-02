# backend-ml/app/vision/embedding.py
import numpy as np
import open_clip
import torch
EMBEDDING_DIM = 768
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
clip_model, _, clip_preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2')
tokenizer = open_clip.get_tokenizer('hf-hub:imageomics/bioclip-2')
clip_model = clip_model.to(DEVICE).eval()

def embed(image):
    with torch.no_grad():
        tensor = clip_preprocess(image).unsqueeze(0).to(DEVICE)  # [1, 3, H, W]
        feat = clip_model.encode_image(tensor)
        feat = feat / feat.norm(dim=-1, keepdim=True)

    return feat.squeeze(0).cpu().numpy()


def embed_batch(images: list):
    """
    Generate embeddings for multiple ROI crops in batch.
    
    Args:
        images: List of PIL Images
    
    Returns:
        List of numpy arrays: embeddings for each image
    """
    if not images:
        return []
    
    with torch.no_grad():
        # Preprocess all images
        tensors = torch.stack([clip_preprocess(img) for img in images]).to(DEVICE)  # [B, 3, H, W]
        feat = clip_model.encode_image(tensors)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    
    return [f.cpu().numpy() for f in feat]
