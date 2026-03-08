# Utilitzem la versió LTS més estable d'Ubuntu com a base
FROM ubuntu:22.04

# Evitem preguntes interactives de configuració durant la instal·lació
ENV DEBIAN_FRONTEND=noninteractive

# Actualitzem el sistema i instal·lem totes les eines per compilar C/C++
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    wget \
    curl \
    ca-certificates \
    libssl-dev \
    libpcre3-dev \
    zlib1g-dev \
    tcpdump \
    iproute2 \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

# Creem i definim la nostra "taula de treball" dins del contenidor
WORKDIR /opt/pqc_workspace

# Comanda per defecte: obrir una consola (bash) en iniciar el contenidor
CMD ["/bin/bash"]