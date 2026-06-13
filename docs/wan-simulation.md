# Simulacio WAN

## Que vol dir latencia WAN

Una latencia WAN (Wide Area Network) es la latencia d'una xarxa d'area ampla, per exemple entre un
client i un servidor en ubicacions geografiques diferents. En una xarxa Docker
local, el RTT acostuma a estar per sota d'1 ms. En una WAN real, el RTT pot ser
molt mes alt:

- mateixa ciutat o regio cloud propera: 5-20 ms;
- entre regions del mateix continent: 20-60 ms;
- entre continents: 80-180 ms o mes.

Una simulacio WAN no converteix Docker en una xarxa real d'Internet, pero permet
afegir retard, jitter i perdua de forma controlada. Aixo es util per estudiar
si l'overhead del key exchange post-quantic continua sent visible quan la xarxa
ja introdueix desenes de mil·lisegons de RTT.

## Es mes realista?

Depen de la pregunta experimental:

- Per mesurar el cost criptografic pur, es millor la xarxa local Docker sense
  retard artificial.
- Per modelar un desplegament distribuït, es mes representatiu introduir RTT,
  jitter i perdua.
- Per reproduir Internet real, una simulacio local continua sent incompleta:
  no modela congestio real, routing variable, peering, buffers d'operadors ni
  TLS middleboxes.

La proposta metodologica es executar els dos modes:

1. benchmark local: estableix el cost base del handshake;
2. benchmark WAN simulat: mostra l'impacte en condicions de xarxa mes properes
   a un desplegament distribuït.

## Implementacio amb tc netem

La simulacio es fa amb `tc netem`, aplicat sobre la interfície `eth0` dels
contenidors. El script `scripts/wan-netem.sh` utilitza la imatge
`nicolaka/netshoot` per entrar al namespace de xarxa de cada servei i aplicar
la disciplina de cua.

Per simular un RTT, el script reparteix el retard entre client i servidor:

```text
retard unidireccional = RTT objectiu / 2
```

Per exemple, `--rtt-ms 40` aplica aproximadament 20 ms a la sortida del client
`bench` i 20 ms a la sortida dels servidors objectiu. El RTT observat queda
proper als 40 ms, amb variacions segons Docker i el sistema host.

## Serveis afectats

El script sempre aplica netem a `bench`, perquè es el client del benchmark. A
mes, aplica la mateixa configuracio als servidors de l'entorn seleccionat:

- `--environment lab`: `server-classic`, `server-hybrid`, `server-pq`;
- `--environment nginx`: `nginx-classic`, `nginx-hybrid`;
- `--environment all`: tots els anteriors.

## Exemple d'us

1. Aixeca l'entorn:

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --remove-orphans
   ```

2. Aplica una WAN simulada de 40 ms RTT, 5 ms de jitter i 0.1% de perdua:

   ```sh
   ./scripts/wan-netem.sh apply --rtt-ms 40 --jitter-ms 5 --loss 0.1 --environment all
   ```

3. Comprova l'estat:

   ```sh
   ./scripts/wan-netem.sh status --environment all
   ```

4. Executa el benchmark:

   ```sh
   python3 scripts/benchmark.py --samples 5 --duration 10 --warmup 2
   ```

5. Desa o reanomena els resultats si vols conservar-los com a WAN:

   ```sh
   cp results/handshake_summary.csv results/handshake_summary_wan_40ms.csv
   cp results/handshake_samples.csv results/handshake_samples_wan_40ms.csv
   cp results/handshake_message_sizes.csv results/handshake_message_sizes_wan_40ms.csv
   ```

6. Neteja la simulacio:

   ```sh
   ./scripts/wan-netem.sh clear --environment all
   ```

## Perfils recomanats

Pots executar diversos perfils i comparar-los:

| Perfil | RTT | Jitter | Perdua | Interpretacio |
| --- | ---: | ---: | ---: | --- |
| Local | 0 ms | 0 ms | 0% | Cost base criptografic i de servidor |
| Regional | 20 ms | 2 ms | 0% | Mateixa regio cloud o xarxa propera |
| Interregional | 60 ms | 5 ms | 0.1% | Regions separades dins d'un continent |
| Intercontinental | 120 ms | 10 ms | 0.1-0.5% | Client i servidor en continents diferents |

## Interpretacio dels resultats

En TLS 1.3, un handshake complet necessita intercanvis de missatges entre client
i servidor. Quan augmenta el RTT, una part important del temps total passa a
dependre de la xarxa. En aquest context, l'overhead criptografic de
`X25519MLKEM768` pot continuar existint, pero pot quedar parcialment amagat per
la latencia de transport.

Aixo no invalida el benchmark local. Els dos resultats responen preguntes
diferents:

- local: quin cost introdueix el canvi criptografic en condicions controlades?
- WAN simulada: quin impacte tindria aquest canvi en una xarxa distribuïda?

## Limitacions

- `tc netem` afegeix retard artificial, pero no modela tota la complexitat
  d'Internet.
- El retard s'aplica dins dels namespaces Docker, no sobre una ruta fisica real.
- La perdua pot afectar TCP amb retransmissions, especialment si s'augmenta
  massa.
- Els resultats amb `s_time` continuen sent mitjanes agregades per lot.
