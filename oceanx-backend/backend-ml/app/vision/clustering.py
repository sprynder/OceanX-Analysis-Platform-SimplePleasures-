# backend-ml/app/vision/clustering.py
import numpy as np
from sklearn.decomposition import PCA
import hdbscan


def cluster_embeddings(embeddings, min_cluster_size=5, pca_components=50):
    """
    Cluster embeddings using HDBSCAN.
    
    Args:
        embeddings: numpy array of shape (n_samples, n_features)
        min_cluster_size: minimum cluster size for HDBSCAN
        pca_components: number of PCA components to reduce to (None to skip)
    
    Returns:
        cluster_labels: numpy array of cluster assignments (-1 for noise)
    """
    n_samples, n_features = embeddings.shape
    
    # Apply PCA dimensionality reduction if requested
    if pca_components is not None:
        pca_dim = min(pca_components, n_samples, n_features)
        embeddings_reduced = PCA(n_components=pca_dim).fit_transform(embeddings)
    else:
        embeddings_reduced = embeddings
    
    # Cluster with HDBSCAN
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric='euclidean',
        cluster_selection_epsilon=0.00,
        max_cluster_size=100,
        cluster_selection_method='leaf'
    )
    
    cluster_labels = clusterer.fit_predict(embeddings_reduced)
    
    return cluster_labels.tolist()
