#!/usr/bin/env sh
set -eu

mkdir -p certs

if [ -f certs/server.crt ] && [ -f certs/server.key ]; then
  echo "certs/server.crt and certs/server.key already exist"
  exit 0
fi

docker run --rm \
  -v "$(pwd)/certs:/certs" \
  openquantumsafe/oqs-ossl3:latest \
  sh -lc '
  /opt/openssl/bin/openssl req \
    -x509 \
    -newkey rsa:2048 \
    -keyout /certs/server.key \
    -out /certs/server.crt \
    -days 365 \
    -nodes \
    -subj "/CN=tfg-pqc.local" \
    -addext "subjectAltName=DNS:classic.tfg-pqc.local,DNS:hybrid.tfg-pqc.local,DNS:pq.tfg-pqc.local,DNS:server-classic,DNS:server-hybrid,DNS:server-pq,DNS:nginx-classic,DNS:nginx-hybrid,DNS:nginx-pq,DNS:localhost"
'

echo "generated certs/server.crt and certs/server.key"
