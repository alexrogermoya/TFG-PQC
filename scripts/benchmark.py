#!/usr/bin/env python3
"""
Mesura experimental per comparar TLS 1.3 classic, hibrid PQC i PQ pur.

La latencia es calcula amb `openssl s_time`, no amb un cronometre Python al
voltant de `docker compose exec`. Aixi OpenSSL i oqsprovider es carreguen una
sola vegada per lot i el valor final representa molts handshakes TLS nous dins
del mateix proces.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"


@dataclass(frozen=True)
class Scenario:
    environment: str
    name: str
    host: str
    group: str

    @property
    def openssl_conf(self) -> str:
        return f"/openssl-config/{self.group.lower()}.cnf"


SCENARIOS = {
    "lab": (
        Scenario("lab", "classic", "server-classic", "X25519"),
        Scenario("lab", "hybrid", "server-hybrid", "X25519MLKEM768"),
        Scenario("lab", "pq", "server-pq", "MLKEM768"),
    ),
    "nginx": (
        Scenario("nginx", "classic", "nginx-classic", "X25519"),
        Scenario("nginx", "hybrid", "nginx-hybrid", "X25519MLKEM768"),
    ),
}


HANDSHAKE_RE = re.compile(
    r"(?P<direction><<<|>>>) TLS 1\.[23], Handshake \[length (?P<length>[0-9a-fA-F]+)\], (?P<name>.+)"
)
TEMP_KEY_RE = re.compile(r"(?:Server|Peer) Temp Key:\s*(?P<key>.+)")
NEGOTIATED_GROUP_RE = re.compile(r"Negotiated TLS1\.3 group:\s*(?P<key>.+)")
STIME_REAL_RE = re.compile(r"(?P<connections>\d+) connections in (?P<seconds>[0-9.]+) real seconds")


def compose_exec_openssl(
    args: list[str],
    *,
    input_text: str = "Q\n",
    openssl_conf: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.nginx.yml",
        "exec",
        "-T",
    ]
    if openssl_conf:
        command.extend(["-e", f"OPENSSL_CONF={openssl_conf}"])
    command.extend([
        "bench",
        "/opt/openssl/bin/openssl",
        *args,
    ])
    return subprocess.run(
        command,
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def run_s_client(scenario: Scenario, *, trace_messages: bool = False) -> str:
    args = [
        "s_client",
        "-connect",
        f"{scenario.host}:443",
        "-servername",
        scenario.host,
        "-tls1_3",
        "-groups",
        scenario.group,
        "-CAfile",
        "/certs/server.crt",
        "-verify_return_error",
        "-brief",
    ]
    if trace_messages:
        args.append("-msg")

    result = compose_exec_openssl(args)
    output = result.stdout + result.stderr

    if result.returncode != 0:
        raise RuntimeError(
            f"Handshake failed for {scenario.name} ({scenario.group}).\n"
            f"Exit code: {result.returncode}\n{output}"
        )

    return output


def run_s_time(scenario: Scenario, *, duration: int) -> tuple[dict[str, float], str]:
    args = [
        "s_time",
        "-connect",
        f"{scenario.host}:443",
        "-tls1_3",
        "-new",
        "-time",
        str(duration),
        "-CAfile",
        "/certs/server.crt",
        "-verify",
        "1",
    ]
    result = compose_exec_openssl(args, input_text="", openssl_conf=scenario.openssl_conf)
    output = result.stdout + result.stderr

    if result.returncode != 0:
        raise RuntimeError(
            f"s_time failed for {scenario.environment}/{scenario.name} ({scenario.group}).\n"
            f"Exit code: {result.returncode}\n{output}"
        )

    matches = list(STIME_REAL_RE.finditer(output))
    if not matches:
        raise RuntimeError(f"Could not parse s_time output for {scenario.environment}/{scenario.name}.\n{output}")

    match = matches[-1]
    connections = int(match.group("connections"))
    real_seconds = float(match.group("seconds"))
    if connections <= 0 or real_seconds <= 0:
        raise RuntimeError(f"Invalid s_time result for {scenario.environment}/{scenario.name}.\n{output}")

    return (
        {
            "connections": connections,
            "real_seconds": real_seconds,
            "mean_ms": (real_seconds * 1000) / connections,
            "handshakes_per_second": connections / real_seconds,
        },
        output,
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    index = round((len(ordered) - 1) * pct)
    return ordered[index]


def parse_negotiated_group(output: str) -> str:
    match = NEGOTIATED_GROUP_RE.search(output) or TEMP_KEY_RE.search(output)
    if not match:
        return "unknown"
    return match.group("key").split(",", maxsplit=1)[0].strip()


def parse_handshake_bytes(output: str) -> dict[str, object]:
    by_direction = {"client_to_server": 0, "server_to_client": 0}
    by_message: dict[str, int] = {}

    for match in HANDSHAKE_RE.finditer(output):
        direction = "server_to_client" if match.group("direction") == "<<<" else "client_to_server"
        length = int(match.group("length"), 16)
        name = match.group("name").strip()
        by_direction[direction] += length
        by_message[name] = by_message.get(name, 0) + length

    return {
        "client_to_server": by_direction["client_to_server"],
        "server_to_client": by_direction["server_to_client"],
        "total_handshake_message_bytes": sum(by_direction.values()),
        "by_message": by_message,
    }


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "samples": len(values),
        "mean_ms": statistics.mean(values),
        "median_ms": statistics.median(values),
        "stdev_ms": statistics.stdev(values) if len(values) > 1 else 0.0,
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "min_ms": min(values),
        "max_ms": max(values),
    }


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark TLS 1.3 classic vs PQC hybrid scenarios")
    parser.add_argument(
        "--environment",
        choices=["lab", "nginx", "all"],
        default="all",
        help="target environment: lab uses openssl s_server; nginx uses the production-like reverse proxy",
    )
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=None,
        help="deprecated; latency is now measured with duration-based s_time batches",
    )
    parser.add_argument("--samples", type=int, default=5, help="s_time batches per scenario")
    parser.add_argument("--duration", type=int, default=5, help="seconds per s_time batch")
    parser.add_argument("--warmup", type=int, default=1, help="warmup seconds per scenario")
    args = parser.parse_args()

    if args.iterations is not None:
        print("Note: --iterations is ignored for latency. Use --samples and --duration instead.")

    RESULTS_DIR.mkdir(exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    sample_rows: list[dict[str, object]] = []
    size_rows: list[dict[str, object]] = []

    selected_scenarios = (
        (*SCENARIOS["lab"], *SCENARIOS["nginx"])
        if args.environment == "all"
        else SCENARIOS[args.environment]
    )

    for scenario in selected_scenarios:
        print(f"[{scenario.environment}/{scenario.name}] warmup: {args.warmup}s with s_time")
        if args.warmup > 0:
            run_s_time(scenario, duration=args.warmup)

        print(f"[{scenario.environment}/{scenario.name}] measuring: {args.samples} x {args.duration}s s_time batches")
        batch_means: list[float] = []
        total_connections = 0
        total_real_seconds = 0.0
        for index in range(1, args.samples + 1):
            timing, _ = run_s_time(scenario, duration=args.duration)
            batch_means.append(timing["mean_ms"])
            total_connections += int(timing["connections"])
            total_real_seconds += timing["real_seconds"]
            sample_rows.append(
                {
                    "environment": scenario.environment,
                    "scenario": scenario.name,
                    "configured_group": scenario.group,
                    "sample": index,
                    "duration_seconds": args.duration,
                    "connections": int(timing["connections"]),
                    "real_seconds": f"{timing['real_seconds']:.6f}",
                    "mean_handshake_ms": f"{timing['mean_ms']:.6f}",
                    "handshakes_per_second": f"{timing['handshakes_per_second']:.6f}",
                }
            )

        traced_output = run_s_client(scenario, trace_messages=True)
        sizes = parse_handshake_bytes(traced_output)
        negotiated_group = parse_negotiated_group(traced_output)
        size_rows.append(
            {
                "environment": scenario.environment,
                "scenario": scenario.name,
                "configured_group": scenario.group,
                "negotiated_group": parse_negotiated_group(traced_output),
                "client_to_server_bytes": sizes["client_to_server"],
                "server_to_client_bytes": sizes["server_to_client"],
                "total_handshake_message_bytes": sizes["total_handshake_message_bytes"],
                "message_breakdown_json": json.dumps(sizes["by_message"], sort_keys=True),
            }
        )

        summary = summarize(batch_means)
        row = {
            "environment": scenario.environment,
            "scenario": scenario.name,
            "configured_group": scenario.group,
            "negotiated_group": negotiated_group,
            "batches": args.samples,
            "total_connections": total_connections,
            "total_real_seconds": f"{total_real_seconds:.6f}",
            "overall_mean_handshake_ms": f"{(total_real_seconds * 1000) / total_connections:.6f}",
            "mean_of_batch_means_ms": f"{summary['mean_ms']:.6f}",
            "median_batch_mean_ms": f"{summary['median_ms']:.6f}",
            "stdev_batch_mean_ms": f"{summary['stdev_ms']:.6f}",
            "p95_batch_mean_ms": f"{summary['p95_ms']:.6f}",
            "p99_batch_mean_ms": f"{summary['p99_ms']:.6f}",
            "min_batch_mean_ms": f"{summary['min_ms']:.6f}",
            "max_batch_mean_ms": f"{summary['max_ms']:.6f}",
            "overall_handshakes_per_second": f"{total_connections / total_real_seconds:.6f}",
            "latency_method": "openssl_s_time_new_connections",
        }
        summary_rows.append(row)

    suffix = args.environment

    sample_fields = [
        "environment",
        "scenario",
        "configured_group",
        "sample",
        "duration_seconds",
        "connections",
        "real_seconds",
        "mean_handshake_ms",
        "handshakes_per_second",
    ]
    summary_fields = [
        "environment",
        "scenario",
        "configured_group",
        "negotiated_group",
        "batches",
        "total_connections",
        "total_real_seconds",
        "overall_mean_handshake_ms",
        "mean_of_batch_means_ms",
        "median_batch_mean_ms",
        "stdev_batch_mean_ms",
        "p95_batch_mean_ms",
        "p99_batch_mean_ms",
        "min_batch_mean_ms",
        "max_batch_mean_ms",
        "overall_handshakes_per_second",
        "latency_method",
    ]
    size_fields = [
        "environment",
        "scenario",
        "configured_group",
        "negotiated_group",
        "client_to_server_bytes",
        "server_to_client_bytes",
        "total_handshake_message_bytes",
        "message_breakdown_json",
    ]

    write_csv(RESULTS_DIR / f"handshake_samples_{suffix}.csv", sample_rows, sample_fields)
    write_csv(RESULTS_DIR / f"handshake_summary_{suffix}.csv", summary_rows, summary_fields)
    write_csv(RESULTS_DIR / f"handshake_message_sizes_{suffix}.csv", size_rows, size_fields)

    write_csv(RESULTS_DIR / "handshake_samples.csv", sample_rows, sample_fields)
    write_csv(RESULTS_DIR / "handshake_summary.csv", summary_rows, summary_fields)
    write_csv(RESULTS_DIR / "handshake_message_sizes.csv", size_rows, size_fields)

    print(f"Results written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
