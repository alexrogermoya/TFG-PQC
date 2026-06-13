# Metodologia experimental

## Objectiu

L'objectiu es comparar el cost de migrar el key exchange de TLS 1.3 cap a
criptografia post-quantica en un entorn controlat i reproduible amb Docker.

La variable principal de l'experiment es el grup TLS negociat:

- `classic`: `X25519`, grup classic elliptic-curve Diffie-Hellman.
- `hybrid`: `X25519MLKEM768`, combinacio hibrida X25519 + ML-KEM-768.
- `pq`: `MLKEM768`, key exchange post-quantic pur.

Els tres serveis utilitzen el mateix certificat RSA autosignat. Aixo evita que
els resultats barregin el cost del key exchange amb diferencies de certificats o
de signatures.

## Arquitectura

El fitxer `docker-compose.yml` crea quatre contenidors principals per al
laboratori aïllat:

- `server-classic`: servidor TLS 1.3 amb `openssl s_server` i grup `X25519`.
- `server-hybrid`: servidor TLS 1.3 amb `openssl s_server` i grup `X25519MLKEM768`.
- `server-pq`: servidor TLS 1.3 amb `openssl s_server` i grup `MLKEM768`.
- `bench`: client OQS/OpenSSL que executa `openssl s_client`.

La imatge base es `openquantumsafe/oqs-ossl3`, que incorpora OpenSSL 3,
liboqs i `oqsprovider`. Aquesta opcio evita construir localment liboqs i fa que
la demo sigui mes facil de reproduir.

El fitxer `docker-compose.nginx.yml` afegeix un segon entorn mes representatiu:

- `nginx-classic`: nginx com a terminador TLS amb `X25519`.
- `nginx-hybrid`: nginx com a terminador TLS amb `X25519MLKEM768`.
- `app-backend`: aplicacio HTTP interna darrere del reverse proxy.

Aquest entorn modela una arquitectura habitual de produccio: el TLS acaba a
nginx, nginx conserva connexions keepalive cap al backend i envia capçaleres
`X-Forwarded-*`. El cas `MLKEM768` pur queda fora del benchmark nginx per una
limitacio practica de la imatge provada: nginx arrenca amb el grup hibrid, pero
falla amb `ssl_ecdh_curve MLKEM768`.

## Metriques

El script `scripts/benchmark.py` recull:

- latencia mitjana del handshake vista pel client amb `openssl s_time`;
- connexions per segon i nombre total de handshakes executats;
- estadistics sobre les mitjanes de cada lot de mesura;
- grup negociat reportat per OpenSSL;
- bytes dels missatges TLS de handshake separats per direccio;
- desglossament aproximat de mida per tipus de missatge TLS.

La latencia no es mesura amb un cronometre de Python al voltant de
`docker compose exec`, perque aixo inclouria crear subprocessos, parlar amb el
daemon de Docker, entrar al contenidor, iniciar OpenSSL i carregar
`oqsprovider`. En canvi, el benchmark usa `openssl s_time -new`: OpenSSL es
carrega una sola vegada i executa molts handshakes nous dins del mateix proces.
No s'envia cap peticio HTTP en aquesta mesura, de manera que el valor se centra
en establir connexions TLS noves. El CSV `handshake_summary.csv` dona la
mitjana global del handshake i els percentils sobre les mitjanes dels lots, no
sobre handshakes individuals.

La mida dels missatges s'obte amb `openssl s_client -msg`, sumant les longituds
dels missatges de handshake que OpenSSL imprimeix. Aquesta metrica es adequada
per comparar l'overhead criptografic entre grups, pero no substitueix una
captura completa de xarxa quan es vol estudiar tamanys de paquets TCP, MTU o
fragmentacio.

La diferencia entre el benchmark antic i l'actual, i el significat de cada CSV,
estan documentats amb mes detall a `docs/benchmark.md`. La descripcio dels
contenidors, fitxers de configuracio i flux d'execucio es troba a
`docs/implementation.md`. Per estudiar l'efecte d'una xarxa distribuïda amb RTT,
jitter i perdua controlats, es pot aplicar la simulacio descrita a
`docs/wan-simulation.md`.

## Execucio

1. Genera el certificat:

   ```sh
   ./scripts/generate-certs.sh
   ```

2. Arrenca els serveis del laboratori i de nginx:

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d
   ```

3. Executa el benchmark complet:

   ```sh
   python3 scripts/benchmark.py --samples 5 --duration 10 --warmup 2
   ```

   El valor per defecte es `--environment all`, per tant s'inclouen `lab` i
   `nginx`. Per executar un sol entorn:

   ```sh
   python3 scripts/benchmark.py --environment lab --samples 5 --duration 10 --warmup 2
   python3 scripts/benchmark.py --environment nginx --samples 5 --duration 10 --warmup 2
   ```

4. Consulta els resultats:

   ```sh
   ls results
   ```

## Captures de xarxa opcionals

Per generar fitxers `.pcap` amb `tcpdump`:

```sh
docker compose --profile capture up -d
python3 scripts/benchmark.py --samples 2 --duration 5 --warmup 1
docker compose --profile capture stop
```

Els fitxers es guarden a `captures/`. Aquesta captura serveix per validar amb
Wireshark el nombre de paquets, bytes TCP/IP totals i possibles fragments.

## Amenaces a la validesa

- L'entorn Docker redueix soroll extern, pero no representa latencia WAN real.
- `openssl s_server` es un servidor de prova, no un reverse proxy de produccio.
  Es molt util per aïllar TLS, pero una extensio futura pot repetir l'experiment
  amb nginx, HAProxy o Envoy compilats contra OpenSSL 3.5/OQS.
- `openssl s_time` dona una mitjana agregada per lot. Per estudiar la
  distribucio exacta handshake a handshake caldria un client persistent propi
  instrumentat amb l'API d'OpenSSL.
