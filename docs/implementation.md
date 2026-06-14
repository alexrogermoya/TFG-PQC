# Implementacio

## Visio general

La implementació conté dos entorns complementaris:

- `lab`: entorn aïllat amb `openssl s_server`, pensat per tenir una referència
  controlada i comparar grups TLS sense cap lògica d'aplicació.
- `nginx`: entorn representatiu amb nginx com a terminador TLS davant d'un
  backend HTTP intern.

Els dos entorns comparteixen certificat i client de benchmark. Aixo permet que
la variable principal sigui el grup TLS negociat, no el material criptografic ni
la versio del client.

## Entorn lab

El fitxer `docker-compose.yml` defineix:

- `server-classic`: `openssl s_server` amb TLS 1.3 i grup `X25519`.
- `server-hybrid`: `openssl s_server` amb TLS 1.3 i grup `X25519MLKEM768`.
- `server-pq`: `openssl s_server` amb TLS 1.3 i grup `MLKEM768`.
- `bench`: contenidor client amb OpenSSL/OQS.
- `capture-*`: contenidors opcionals amb `tcpdump`.

Els tres servidors `lab` utilitzen `openquantumsafe/oqs-ossl3:latest`. Les
ordres de servidor son equivalents excepte pel grup:

```text
/opt/openssl/bin/openssl s_server -accept 443 -cert /certs/server.crt \
  -key /certs/server.key -www -tls1_3 -no_ticket -groups <GRUP>
```

`-no_ticket` desactiva tickets de sessio per evitar que la reutilitzacio de
sessio contamini la comparacio de handshakes nous.

## Entorn nginx

El fitxer `docker-compose.nginx.yml` afegeix:

- `nginx-classic`: nginx amb `ssl_ecdh_curve X25519`.
- `nginx-hybrid`: nginx amb `ssl_ecdh_curve X25519MLKEM768`.
- `nginx-pq`: nginx amb `ssl_ecdh_curve mlkem768`.
- `app-backend`: backend HTTP intern basat en `nginx:alpine`.

Aquest entorn modela una arquitectura mes propera a produccio:

```text
client bench -> nginx TLS -> backend HTTP intern
```

Nginx termina TLS al port 443 del contenidor i publica ports al host:

- `8441`: `nginx-classic`
- `8442`: `nginx-hybrid`
- `8443`: `nginx-pq`

El backend escolta HTTP intern al port 8080. Nginx hi fa `proxy_pass` i envia
capçaleres habituals de reverse proxy:

- `Host`
- `X-Forwarded-Proto`
- `X-Forwarded-For`

La configuracio tambe activa `keepalive 32` cap al backend. Aixo no afecta la
mesura TLS directa amb `s_time`, pero fa que l'entorn sigui mes semblant a un
reverse proxy real.

## Per que no hi ha nginx-pq actiu

Hi ha un fitxer `configs/nginx/pq.conf`, pero el servei `nginx-pq` no forma
part del perfil per defecte. Durant la validacio, la imatge
`openquantumsafe/nginx:latest` acceptava `X25519` i `X25519MLKEM768`, pero
fallava en arrencar amb:

```text
SSL_CTX_set1_curves_list("MLKEM768") failed
```

Per aquest motiu, el cas `MLKEM768` pur queda limitat a l'entorn `lab`. Aquesta
limitacio es rellevant per al TFG: en un servidor web realista, la transicio
practica observada es cap a TLS hibrid, no cap a PQ pur.

## Certificats

El script `scripts/generate-certs.sh` genera:

- `certs/server.crt`
- `certs/server.key`

El certificat es RSA autosignat i inclou SANs per als noms interns:

- `server-classic`
- `server-hybrid`
- `server-pq`
- `nginx-classic`
- `nginx-hybrid`
- `nginx-pq`
- `localhost`

S'utilitza el mateix certificat en tots els escenaris per no barrejar el cost
del key exchange amb diferencies en el certificat.

## Client de benchmark

El servei `bench` utilitza `openquantumsafe/oqs-ossl3:latest` i munta:

- `./certs:/certs`
- `./configs/openssl:/openssl-config:ro`

Les configuracions d'OpenSSL dins `configs/openssl/` forcen el grup que anuncia
el client quan s'executa `openssl s_time`. Aixo es necessari perquè `s_time` no
te opcio `-groups`, mentre que `s_client` si que la te.

## Flux d'execucio

1. Es genera el certificat:

   ```sh
   ./scripts/generate-certs.sh
   ```

2. S'aixequen els serveis:

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --remove-orphans
   ```

3. S'executa el benchmark:

   ```sh
   python3 scripts/benchmark.py --samples 5 --duration 10 --warmup 2
   ```

4. El script recorre els escenaris seleccionats, fa un warmup, executa lots
   `s_time`, inspecciona un handshake amb `s_client -msg` i escriu els CSV.

## Captura de trafic

Els serveis `capture-classic`, `capture-hybrid` i `capture-pq` usen
`nicolaka/netshoot` amb `tcpdump`. Es llancen nomes amb el perfil `capture`.

```sh
docker compose --profile capture up -d
python3 scripts/benchmark.py --environment lab --samples 2 --duration 5 --warmup 1
docker compose --profile capture stop
```

Els fitxers `.pcap` es guarden a `captures/`. Serveixen per validar paquets,
fragmentacio i bytes TCP/IP totals amb Wireshark.

## Simulacio WAN

La simulacio WAN es gestiona amb `scripts/wan-netem.sh`. El script no crea nous
servidors: aplica `tc netem` als namespaces de xarxa dels contenidors existents.
Aixo permet reutilitzar exactament la mateixa implementacio `lab` i `nginx`, i
canviar nomes les condicions de xarxa.

Internament, el script llança contenidors temporals `nicolaka/netshoot` amb:

```text
--network container:<container-id> --cap-add NET_ADMIN
```

Aixi pot executar `tc qdisc replace dev eth0 root netem ...` dins la xarxa del
servei objectiu sense instal·lar eines addicionals a les imatges OQS o nginx.
