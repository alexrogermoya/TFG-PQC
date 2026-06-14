#!/bin/bash

# Aturar el script immediatament si alguna comanda falla
set -e

# Variable per escurçar la crida a Docker Compose
COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.nginx.yml"

# Neteja inicial per assegurar un estat net
echo "[!] Realitzant neteja inicial..."
$COMPOSE_CMD down -v
echo ""

# Funció genèrica per executar qualsevol escenari
run_scenario() {
    local SCENARIO_NAME=$1
    local RTT=$2
    local JITTER=$3
    local LOSS=$4
    local IS_WAN=$5

    echo "========================================================"
    echo " INICIANT ESCENARI: $SCENARIO_NAME"
    echo "========================================================"

    # 1. Arrencar contenidors i iniciar captures
    echo "[+] Aixecant contenidors i iniciant captures de xarxa..."
    $COMPOSE_CMD --profile capture up -d
    sleep 5

    # 2. Injectar latència (Només si és un entorn WAN)
    if [ "$IS_WAN" = "true" ]; then
        echo "[+] Injectant latència WAN: RTT=${RTT}ms, Jitter=${JITTER}ms, Loss=${LOSS}%"
        ./scripts/wan-netem.sh apply --rtt-ms "$RTT" --jitter-ms "$JITTER" --loss "$LOSS" --environment nginx
        NETWORK_ARG="wan"
    else
        echo "[+] Entorn local (sense injecció de latència)."
        NETWORK_ARG="local"
    fi

    # 3. Executar benchmark
    echo "[+] Executant proves de rendiment amb Python..."
    python3 scripts/benchmark.py --samples 10 --duration 30 --warmup 2 --network "$NETWORK_ARG"
    # python3 scripts/benchmark.py --samples 1 --duration 2 --warmup 0 --network "$NETWORK_ARG"

    # 4. Tancar captures ordenadament per guardar els PCAP
    echo "[+] Aturant contenidors de captura..."
    $COMPOSE_CMD --profile capture stop
    sleep 2

    # 5. Renombrar resultats CSV (Només WAN, els de local ja es guarden correctament)
    if [ "$IS_WAN" = "true" ]; then
        echo "[+] Renombrant arxius CSV..."
        mv results/handshake_summary_all_wan.csv results/handshake_summary_all_${SCENARIO_NAME}.csv
        mv results/handshake_samples_all_wan.csv results/handshake_samples_all_${SCENARIO_NAME}.csv
        mv results/handshake_message_sizes_all_wan.csv results/handshake_message_sizes_all_${SCENARIO_NAME}.csv
    fi

    # 6. Renombrar PCAPs (S'utilitza mv per evitar contaminació entre proves)
    echo "[+] Renombrant captures PCAP..."
    # L'ús de "2>/dev/null || true" evita que el script falli si algun PCAP no s'ha generat
    mv captures/classic.pcap captures/classic_${SCENARIO_NAME}.pcap 2>/dev/null || true
    mv captures/classic_nginx.pcap captures/classic_nginx_${SCENARIO_NAME}.pcap 2>/dev/null || true
    mv captures/hybrid.pcap captures/hybrid_${SCENARIO_NAME}.pcap 2>/dev/null || true
    mv captures/hybrid_nginx.pcap captures/hybrid_nginx_${SCENARIO_NAME}.pcap 2>/dev/null || true
    mv captures/pq.pcap captures/pq_${SCENARIO_NAME}.pcap 2>/dev/null || true
    mv captures/pq_nginx.pcap captures/pq_nginx_${SCENARIO_NAME}.pcap 2>/dev/null || true

    # 7. Apagar contenidors
    echo "[+] Apagant l'entorn i netejant volums..."
    $COMPOSE_CMD down -v

    echo "[✓] Escenari $SCENARIO_NAME completat amb èxit."
    echo ""
}

# Execució seqüencial de tots els teus escenaris:
#            Nom de l'escenari      RTT  Jitter  Loss  És_WAN?
run_scenario "local"                0    0       0     "false"
run_scenario "wan_regional"         40   5       0.1   "true"
run_scenario "wan_interregional"    120  10      0.5   "true"
run_scenario "wan_intercontinental" 250  20      1.0   "true"

echo "Totes les simulacions i benchmarks han finalitzat correctament!"

python3 scripts/create_lab_plots.py
python3 scripts/create_plots_full.py
python3 scripts/create_plots.py