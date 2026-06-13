# Benchmark

La versio actual separa dues mesures:

- latencia: `openssl s_time -new`, amb molts handshakes nous dins d'un mateix
  proces OpenSSL;
- mida dels missatges: `openssl s_client -msg`, executat una vegada per escenari
  per inspeccionar el handshake.

Amb `s_time`, OpenSSL i `oqsprovider` es carreguen una sola vegada per lot. El
resultat representa el cost mitja d'establir connexions TLS noves, no el cost
d'orquestrar Docker i iniciar binaris.

## Que mesura exactament la latencia

Per cada escenari, el script executa:

```text
openssl s_time -connect <host>:443 -tls1_3 -new -time <duration> -CAfile /certs/server.crt -verify 1
```

El flag `-new` força connexions noves i evita mesurar reutilitzacio de sessio.
No s'utilitza `-www`, de manera que no s'envia una petició HTTP posterior al
handshake. La metrica se centra en establir connexions TLS noves.

El script força el grup TLS anunciat pel client amb `OPENSSL_CONF`, perquè
`s_time` no accepta `-groups`. Cada escenari apunta a una configuracio:

- `X25519`: `/openssl-config/x25519.cnf`
- `X25519MLKEM768`: `/openssl-config/x25519mlkem768.cnf`
- `MLKEM768`: `/openssl-config/mlkem768.cnf`

Aquestes configuracions es munten al contenidor `bench` des de
`configs/openssl/`.

## Parametres

```sh
python3 scripts/benchmark.py --samples 5 --duration 10 --warmup 2
```

- `--environment`: `lab`, `nginx` o `all`. Per defecte és `all`.
- `--network`: `local`, `wan`. Per defecte és `local`.
- `--samples`: nombre de lots `s_time` per escenari.
- `--duration`: segons de cada lot.
- `--warmup`: segons previs per escalfar el cami de codi abans de mesurar.
- `--iterations`: es conserva nomes per compatibilitat, pero ja no governa la
  latència.

Un lot no dona una mostra handshake a handshake. Dona una mitjana agregada:

```text
mean_handshake_ms = real_seconds * 1000 / connections
```

Els percentils del resum (`p95_batch_mean_ms`, `p99_batch_mean_ms`) son
percentils de les mitjanes dels lots, no percentils de cada handshake individual.

## Fitxers de sortida

El directori `results/` conte:

- `handshake_samples.csv`: una fila per lot de mesura.
- `handshake_summary.csv`: resum agregat per escenari.
- `handshake_message_sizes.csv`: mida dels missatges TLS de handshake.
- `handshake_samples_<environment>.csv`,
  `handshake_summary_<environment>.csv` i
  `handshake_message_sizes_<environment>.csv`: copia amb sufix de l'entorn
  executat.

## Columnes principals

`handshake_samples.csv`:

- `environment`: `lab` o `nginx`.
- `scenario`: `classic`, `hybrid` o `pq`.
- `configured_group`: grup TLS configurat.
- `sample`: número de lot.
- `duration_seconds`: durada sol·licitada per lot.
- `connections`: connexions TLS noves completades per `s_time`.
- `real_seconds`: temps real reportat per `s_time`.
- `mean_handshake_ms`: latència mitjana del lot.
- `handshakes_per_second`: throughput de handshakes nous.

`handshake_summary.csv`:

- `overall_mean_handshake_ms`: mitjana global ponderada per totes les connexions.
- `mean_of_batch_means_ms`: mitjana simple de les mitjanes dels lots.
- `median_batch_mean_ms`: mediana de les mitjanes dels lots.
- `stdev_batch_mean_ms`: desviació estandard entre lots.
- `overall_handshakes_per_second`: throughput global.
- `latency_method`: metode utilitzat per obtenir la latència.

`handshake_message_sizes.csv`:

- `client_to_server_bytes`: suma dels missatges handshake client -> servidor.
- `server_to_client_bytes`: suma dels missatges handshake servidor -> client.
- `total_handshake_message_bytes`: suma total dels missatges handshake.
- `message_breakdown_json`: desglossament per tipus de missatge TLS.

## Interpretacio

La comparació important no es el valor absolut d'una sola fila, sinó la relació
entre escenaris sota les mateixes condicions. Per exemple:

- `classic` dona la base amb X25519.
- `hybrid` mostra el cost d'afegir ML-KEM al key exchange.
- `pq` permet veure el cas post-quantic pur al laboratori aïllat.
- `nginx` mostra l'efecte en un servidor web representatiu.

El benchmark actual es mes adequat que l'anterior per estimar latencia TLS
perque elimina el cost de crear processos per cada mostra. Per defecte continua
sent una mesura local en Docker. Si es vol modelar una xarxa distribuïda, es pot
afegir una simulació WAN amb `tc netem`, documentada a `docs/wan-simulation.md`.
