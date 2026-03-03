FROM apache/spark:python3-java17

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    ca-certificates \
    && wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-py311_24.5.0-0-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && ln -sf /opt/conda/bin/python /usr/bin/python3 \
    && ln -sf /opt/conda/bin/python /usr/bin/python \
    && rm -f /tmp/miniconda.sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/conda/bin:${PATH}"
ENV PYSPARK_PYTHON=/opt/conda/bin/python
ENV PYSPARK_DRIVER_PYTHON=/opt/conda/bin/python

USER spark
