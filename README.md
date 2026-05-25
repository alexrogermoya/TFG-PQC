# Transicio a TLS post-quantic hibrid

Entorn Docker per demostrar i mesurar una migracio TLS 1.3 des d'un key
exchange classic cap a una estructura hibrida post-quantica.

## Que es construeix

La demo aixeca tres servidors TLS comparables:

- `classic`: TLS 1.3 amb `X25519`.
- `hybrid`: TLS 1.3 amb `X25519MLKEM768`.
- `pq`: TLS 1.3 amb `MLKEM768`.

Tots tres fan servir la imatge `openquantumsafe/oqs-ossl3`, basada en OpenSSL 3
amb liboqs i `oqsprovider`, i comparteixen el mateix certificat RSA autosignat.
Aixi l'experiment aïlla l'efecte del grup de key exchange.

També hi ha un segon entorn, mes representatiu, amb nginx com a reverse proxy
TLS davant d'una aplicacio HTTP interna. Aquest entorn compara `X25519` contra
`X25519MLKEM768`. El cas `MLKEM768` pur es conserva al laboratori amb
`openssl s_server`, perque la imatge nginx/OQS provada no accepta `MLKEM768`
pur amb la directiva `ssl_ecdh_curve`.

## Posada en marxa

```sh
./scripts/generate-certs.sh
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d
python3 scripts/benchmark.py --samples 5 --duration 10 --warmup 2
```

Per executar nomes l'entorn nginx:

```sh
python3 scripts/benchmark.py --environment nginx --samples 5 --duration 10 --warmup 2
```

Per executar nomes el laboratori aïllat:

```sh
python3 scripts/benchmark.py --environment lab --samples 5 --duration 10 --warmup 2
```

Els CSV es generen a `results/`:

- `handshake_samples.csv`: una fila per lot de mesura `s_time`.
- `handshake_summary.csv`: estadistics agregats de latencia del handshake.
- `handshake_message_sizes.csv`: overhead dels missatges de handshake.
- `handshake_*_all.csv`, `handshake_*_lab.csv` o `handshake_*_nginx.csv`: copia amb sufix segons l'entorn executat.

## Verificacio manual

```sh
docker compose exec bench /opt/openssl/bin/openssl s_client \
  -connect server-hybrid:443 \
  -servername server-hybrid \
  -tls1_3 \
  -groups X25519MLKEM768 \
  -CAfile /certs/server.crt \
  -brief
```

La sortida hauria d'indicar `Negotiated TLS1.3 group: X25519MLKEM768`.

Per verificar nginx:

```sh
docker compose -f docker-compose.yml -f docker-compose.nginx.yml exec bench \
  /opt/openssl/bin/openssl s_client \
  -connect nginx-hybrid:443 \
  -servername nginx-hybrid \
  -tls1_3 \
  -groups X25519MLKEM768 \
  -CAfile /certs/server.crt \
  -brief
```

## Captures pcap opcionals

```sh
docker compose --profile capture up -d
python3 scripts/benchmark.py --samples 2 --duration 5 --warmup 1
docker compose --profile capture stop
```

Els `.pcap` queden a `captures/` i es poden obrir amb Wireshark.

## Simulacio WAN

Per estudiar un escenari distribuït amb RTT, jitter i perdua controlats:

```sh
./scripts/wan-netem.sh apply --rtt-ms 40 --jitter-ms 5 --loss 0.1 --environment all
python3 scripts/benchmark.py --samples 5 --duration 10 --warmup 2
./scripts/wan-netem.sh clear --environment all
```

El detall esta documentat a `docs/wan-simulation.md`.

## Metodologia

La metodologia completa esta descrita a `docs/methodology.md`. El detall del
benchmark esta a `docs/benchmark.md` i el detall de la implementacio a
`docs/implementation.md`. La simulacio WAN esta a `docs/wan-simulation.md`.
