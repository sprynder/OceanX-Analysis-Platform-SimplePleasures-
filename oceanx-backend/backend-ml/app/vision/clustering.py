# backend-ml/app/vision/clustering.py
import numpy as np
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans as SklearnKMeans
import hdbscan
import logging


logger = logging.getLogger(__name__)


def _sanitize_embeddings(embeddings):
    embeddings_array = np.asarray(embeddings, dtype=np.float64)
    if embeddings_array.ndim != 2:
        raise ValueError('embeddings must be a 2D array')
    return np.nan_to_num(embeddings_array, nan=0.0, posinf=0.0, neginf=0.0)


def _apply_sklearn_pca(embeddings, pca_components):
    n_samples, n_features = embeddings.shape
    pca_dim = min(pca_components, n_samples, n_features)
    if pca_dim <= 0:
        return embeddings
    return PCA(n_components=pca_dim).fit_transform(embeddings)


def _cluster_embeddings_hdbscan(
    embeddings,
    min_cluster_size=5,
    min_samples=None,
    cluster_selection_epsilon=0.0,
    max_cluster_size=None,
    cluster_selection_method='eom',
    pca_components=50,
):
    n_samples = len(embeddings)
    if n_samples == 0:
        return []


    if pca_components is not None:
        embeddings_reduced = _apply_sklearn_pca(embeddings, pca_components)
    else:
        embeddings_reduced = embeddings

    # Normalize HDBSCAN parameters
    # hdbscan expects max_cluster_size to be an int (0 = no limit)
    max_cluster_size_value = 0 if max_cluster_size is None else max_cluster_size

    # Cluster with HDBSCAN
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_epsilon=cluster_selection_epsilon,
        max_cluster_size=max_cluster_size_value,
        cluster_selection_method=cluster_selection_method
    )
    
    cluster_labels = clusterer.fit_predict(embeddings_reduced)
    
    return cluster_labels.tolist()


def _cluster_embeddings_sklearn_kmeans(
    embeddings,
    kmeans_k=8,
    pca_components=50,
    kmeans_seed=42,
    kmeans_max_iter=20,
):
    n_samples, n_features = embeddings.shape
    if n_samples == 0:
        return []
    if n_samples == 1:
        return [0]

    kmeans_k = max(2, min(int(kmeans_k), n_samples))

    transformed_embeddings = embeddings
    if pca_components is not None:
        pca_dim = max(1, min(int(pca_components), n_samples, n_features))
        transformed_embeddings = PCA(n_components=pca_dim).fit_transform(embeddings)

    model = SklearnKMeans(
        n_clusters=kmeans_k,
        random_state=int(kmeans_seed),
        max_iter=int(kmeans_max_iter),
        n_init='auto',
    )
    labels = model.fit_predict(transformed_embeddings)
    return labels.astype(int).tolist()


def _cluster_embeddings_spark_kmeans(
    embeddings,
    kmeans_k=8,
    pca_components=50,
    kmeans_seed=42,
    kmeans_max_iter=20,
    spark_master='local[*]',
    spark_app_name='oceanx-clustering-kmeans',
):
    if len(embeddings) == 0:
        return []

    print('[SparkKMeans] Starting Spark kmeans pipeline', flush=True)

    import importlib

    ml_clustering = importlib.import_module('pyspark.ml.clustering')
    ml_feature = importlib.import_module('pyspark.ml.feature')
    ml_linalg = importlib.import_module('pyspark.ml.linalg')
    spark_sql = importlib.import_module('pyspark.sql')
    spark_types = importlib.import_module('pyspark.sql.types')

    KMeans = ml_clustering.KMeans
    SparkPCA = ml_feature.PCA
    Vectors = ml_linalg.Vectors
    VectorUDT = ml_linalg.VectorUDT
    SparkSession = spark_sql.SparkSession
    T = spark_types

    n_samples, n_features = embeddings.shape
    print(f'[SparkKMeans] Input embeddings shape: n_samples={n_samples}, n_features={n_features}', flush=True)

    if n_samples == 1:
        return [0]

    kmeans_k = max(2, min(int(kmeans_k), n_samples))
    print(f'[SparkKMeans] Effective k={kmeans_k}, pca_components={pca_components}', flush=True)

    spark = None
    try:
        netlib_java_opts = (
            '-Dcom.github.fommil.netlib.BLAS=com.github.fommil.netlib.F2jBLAS '
            '-Dcom.github.fommil.netlib.LAPACK=com.github.fommil.netlib.F2jLAPACK'
        )

        spark = (
            SparkSession.builder
            .master(spark_master)
            .appName(spark_app_name)
            .config('spark.ui.enabled', 'false')
            .config('spark.ui.showConsoleProgress', 'false')
            .config('spark.port.maxRetries', '64')
            .config('spark.driver.host', '127.0.0.1')
            .config('spark.driver.bindAddress', '127.0.0.1')
            .config('spark.python.use.daemon', 'true')
            .config('spark.python.worker.reuse', 'true')
            .config('spark.python.worker.faulthandler.enabled', 'true')
            .config('spark.sql.execution.pyspark.udf.faulthandler.enabled', 'true')
            .config('spark.driver.extraJavaOptions', netlib_java_opts)
            .config('spark.executor.extraJavaOptions', netlib_java_opts)
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel('ERROR')
        print('[SparkKMeans] Spark session created', flush=True)

        schema = T.StructType([
            T.StructField('row_id', T.IntegerType(), False),
            T.StructField('features', VectorUDT(), False),
        ])

        rows = [
            (idx, Vectors.dense([float(value) for value in vector]))
            for idx, vector in enumerate(embeddings)
        ]
        df = spark.createDataFrame(rows, schema=schema)
        print(f'[SparkKMeans] DataFrame created with {len(rows)} rows', flush=True)

        transformed_df = df
        if pca_components is not None:
            pca_dim = max(1, min(int(pca_components), n_samples, n_features))
            print(f'[SparkKMeans] Fitting Spark PCA with k={pca_dim}', flush=True)
            pca_model = SparkPCA(k=pca_dim, inputCol='features', outputCol='features_pca').fit(df)
            transformed_df = pca_model.transform(df).select('row_id', 'features_pca')
            transformed_df = transformed_df.withColumnRenamed('features_pca', 'features')
            print('[SparkKMeans] Spark PCA transform completed', flush=True)
        else:
            print('[SparkKMeans] PCA skipped (pca_components is None)', flush=True)

        kmeans = KMeans(
            k=kmeans_k,
            seed=int(kmeans_seed),
            maxIter=int(kmeans_max_iter),
            featuresCol='features',
            predictionCol='cluster_id',
        )
        print(f'[SparkKMeans] Fitting Spark KMeans (maxIter={int(kmeans_max_iter)}, seed={int(kmeans_seed)})', flush=True)
        model = kmeans.fit(transformed_df)
        print('[SparkKMeans] Spark KMeans fit completed', flush=True)

        predictions = model.transform(transformed_df).select('row_id', 'cluster_id').collect()
        print(f'[SparkKMeans] Collected predictions for {len(predictions)} rows', flush=True)
        labels = [0] * n_samples
        for row in predictions:
            labels[row['row_id']] = int(row['cluster_id'])

        print('[SparkKMeans] Pipeline finished successfully', flush=True)
        return labels
    except Exception as exc:
        print(f'[SparkKMeans] Pipeline failed: {exc}', flush=True)
        raise
    finally:
        if spark is not None:
            try:
                spark.stop()
                print('[SparkKMeans] Spark session stopped', flush=True)
            except Exception:
                print('[SparkKMeans] Spark session stop failed (ignored)', flush=True)
                logger.debug('Failed to stop Spark session cleanly', exc_info=True)


def cluster_embeddings(
    embeddings,
    algorithm='hdbscan',
    min_cluster_size=5,
    min_samples=None,
    cluster_selection_epsilon=0.0,
    max_cluster_size=None,
    cluster_selection_method='eom',
    pca_components=50,
    kmeans_k=8,
    kmeans_seed=42,
    kmeans_max_iter=20,
    use_spark_kmeans=True,
    spark_master='local[*]',
    spark_app_name='oceanx-clustering-kmeans',
):
    embeddings = _sanitize_embeddings(embeddings)

    if algorithm == 'hdbscan':
        return _cluster_embeddings_hdbscan(
            embeddings,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
            max_cluster_size=max_cluster_size,
            cluster_selection_method=cluster_selection_method,
            pca_components=pca_components,
        )

    if algorithm == 'kmeans':
        if not use_spark_kmeans:
            print('[Cluster] Using sklearn kmeans path (Spark disabled)', flush=True)
            return _cluster_embeddings_sklearn_kmeans(
                embeddings,
                kmeans_k=kmeans_k,
                pca_components=pca_components,
                kmeans_seed=kmeans_seed,
                kmeans_max_iter=kmeans_max_iter,
            )

        try:
            print('[Cluster] Using Spark kmeans path', flush=True)
            return _cluster_embeddings_spark_kmeans(
                embeddings,
                kmeans_k=kmeans_k,
                pca_components=pca_components,
                kmeans_seed=kmeans_seed,
                kmeans_max_iter=kmeans_max_iter,
                spark_master=spark_master,
                spark_app_name=spark_app_name,
            )
        except Exception:
            print('[Cluster] Spark kmeans failed; falling back to sklearn kmeans', flush=True)
            logger.exception('Spark kmeans failed; falling back to sklearn kmeans')
            return _cluster_embeddings_sklearn_kmeans(
                embeddings,
                kmeans_k=kmeans_k,
                pca_components=pca_components,
                kmeans_seed=kmeans_seed,
                kmeans_max_iter=kmeans_max_iter,
            )

    raise ValueError(f'Unsupported clustering algorithm: {algorithm}')
