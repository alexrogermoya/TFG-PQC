#!/usr/bin/env sh
set -eu

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.nginx.yml"
ACTION="${1:-}"

usage() {
  cat <<'EOF'
Usage:
  scripts/wan-netem.sh apply [--rtt-ms N] [--jitter-ms N] [--loss PCT] [--environment all|lab|nginx]
  scripts/wan-netem.sh clear [--environment all|lab|nginx]
  scripts/wan-netem.sh status [--environment all|lab|nginx]

Examples:
  scripts/wan-netem.sh apply --rtt-ms 40 --jitter-ms 5 --loss 0.1 --environment nginx
  scripts/wan-netem.sh status --environment all
  scripts/wan-netem.sh clear --environment all
EOF
}

if [ -z "$ACTION" ]; then
  usage
  exit 1
fi

if [ "$ACTION" = "-h" ] || [ "$ACTION" = "--help" ]; then
  usage
  exit 0
fi

shift || true

RTT_MS=40
JITTER_MS=0
LOSS_PCT=0
ENVIRONMENT=all

while [ "$#" -gt 0 ]; do
  case "$1" in
    --rtt-ms)
      RTT_MS="$2"
      shift 2
      ;;
    --jitter-ms)
      JITTER_MS="$2"
      shift 2
      ;;
    --loss)
      LOSS_PCT="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$ACTION" in
  apply|clear|status) ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage
    exit 1
    ;;
esac

case "$ENVIRONMENT" in
  all)
    TARGET_SERVICES="server-classic server-hybrid server-pq nginx-classic nginx-hybrid"
    ;;
  lab)
    TARGET_SERVICES="server-classic server-hybrid server-pq"
    ;;
  nginx)
    TARGET_SERVICES="nginx-classic nginx-hybrid"
    ;;
  *)
    echo "Unknown environment: $ENVIRONMENT" >&2
    usage
    exit 1
    ;;
esac

SERVICES="bench $TARGET_SERVICES"
ONE_WAY_MS=$(awk "BEGIN { printf \"%.3f\", $RTT_MS / 2 }")

container_id_for_service() {
  docker compose $COMPOSE_FILES ps -q "$1"
}

run_netshoot() {
  service="$1"
  shift
  container_id="$(container_id_for_service "$service")"
  if [ -z "$container_id" ]; then
    echo "Service is not running: $service" >&2
    echo "Start the environment first with:" >&2
    echo "  docker compose $COMPOSE_FILES up -d --remove-orphans" >&2
    exit 1
  fi

  docker run --rm \
    --network "container:$container_id" \
    --cap-add NET_ADMIN \
    nicolaka/netshoot:latest \
    "$@"
}

for service in $SERVICES; do
  case "$ACTION" in
    apply)
      echo "Applying WAN netem to $service: ${ONE_WAY_MS}ms one-way, ${JITTER_MS}ms jitter, ${LOSS_PCT}% loss"
      if [ "$LOSS_PCT" = "0" ] || [ "$LOSS_PCT" = "0.0" ]; then
        run_netshoot "$service" tc qdisc replace dev eth0 root netem delay "${ONE_WAY_MS}ms" "${JITTER_MS}ms"
      else
        run_netshoot "$service" tc qdisc replace dev eth0 root netem delay "${ONE_WAY_MS}ms" "${JITTER_MS}ms" loss "${LOSS_PCT}%"
      fi
      ;;
    clear)
      echo "Clearing WAN netem from $service"
      run_netshoot "$service" sh -lc 'tc qdisc del dev eth0 root 2>/dev/null || true'
      ;;
    status)
      echo "[$service]"
      run_netshoot "$service" tc qdisc show dev eth0
      ;;
  esac
done
