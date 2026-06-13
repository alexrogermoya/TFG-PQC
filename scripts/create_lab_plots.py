import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

arxiu_summary = "results/handshake_summary_all_local.csv"
arxiu_sizes = "results/handshake_message_sizes_all_local.csv"

if not os.path.exists(arxiu_summary) or not os.path.exists(arxiu_sizes):
    print(f"[ERROR] No es troben els arxius _local.csv a la carpeta results/.")
    exit(1)

# Llegim les dades
df_sum = pd.read_csv(arxiu_summary)
df_siz = pd.read_csv(arxiu_sizes)

# Filtrem exclusivament per l'entorn LAB
lab_sum = df_sum[df_sum["environment"] == "lab"].set_index("scenario")
lab_siz = df_siz[df_siz["environment"] == "lab"].set_index("scenario")

# Ordre d'escenaris i colors
escenaris = ["classic", "hybrid", "pq"]
lab_sum = lab_sum.reindex(escenaris)
lab_siz = lab_siz.reindex(escenaris)

noms_x = ["Clàssic\n(X25519)", "Híbrid\n(X25519+ML-KEM)", "PQ Pur\n(ML-KEM)"]
x = np.arange(len(escenaris))
width = 0.5

colors_bar = ["#4C72B0", "#DD8452", "#55A868"]

def aplicar_estil_academic(ax):
    """Funció d'estil: Manté l'eix esquerre i inferior (format L), treu el de dalt i la dreta."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

# ==========================================
# 1. DIRECCIONALITAT
# ==========================================
fig2, ax2 = plt.subplots(figsize=(7, 5))
c2s = lab_siz["client_to_server_bytes"]
s2c = lab_siz["server_to_client_bytes"]

p1 = ax2.bar(x, c2s, width, label='Client -> Servidor', color="#854FBE", zorder=3)
p2 = ax2.bar(x, s2c, width, bottom=c2s, label='Servidor -> Client', color='#C44E52', zorder=3)

totals = c2s + s2c
for i, total in enumerate(totals):
    if not np.isnan(total):
        ax2.text(x[i], total + 50, f"{int(total)} B", ha='center', fontweight='bold')

ax2.set_ylabel("Bytes", fontsize=11, fontweight="bold")
ax2.set_title("Trànsit Direccional (Entorn LAB)", fontsize=13, fontweight="bold")
ax2.axhline(y=1500, color="#31AE44", linestyle='-.', label='Límit MTU (~1500 B)', zorder=4)
ax2.set_xticks(x)
ax2.set_xticklabels(noms_x, fontsize=10)
ax2.legend(frameon=True, edgecolor='black')

aplicar_estil_academic(ax2)
plt.tight_layout()
fig2.savefig("results/annex_lab_directional.png", dpi=300)

# ==========================================
# 2. TEMPS DE HANDSHAKE (Mitjana)
# ==========================================
fig3, ax3 = plt.subplots(figsize=(7, 5))
b3 = ax3.bar(x, lab_sum["overall_mean_handshake_ms"], width, color=colors_bar, zorder=3)
ax3.bar_label(b3, fmt="%.2f ms", padding=3, fontsize=10)
ax3.set_ylabel("Temps de Handshake (ms)", fontsize=11, fontweight="bold")
ax3.set_title("Cost de CPU pur: Temps d'establiment (Entorn LAB)", fontsize=13, fontweight="bold")
ax3.set_xticks(x)
ax3.set_xticklabels(noms_x, fontsize=10)
ax3.set_ylim(0, max(lab_sum["overall_mean_handshake_ms"]) * 1.15)

aplicar_estil_academic(ax3)
plt.tight_layout()
fig3.savefig("results/annex_lab_time.png", dpi=300)

# ==========================================
# 3. THROUGHPUT (Connexions per segon)
# ==========================================
fig4, ax4 = plt.subplots(figsize=(7, 5))
b4 = ax4.bar(x, lab_sum["overall_handshakes_per_second"], width, color=colors_bar, zorder=3)
ax4.bar_label(b4, fmt="%.0f", padding=3, fontsize=10)
ax4.set_ylabel("Connexions/segon", fontsize=11, fontweight="bold")
ax4.set_title("Capacitat del servidor aïllat (Throughput - LAB)", fontsize=13, fontweight="bold")
ax4.set_xticks(x)
ax4.set_xticklabels(noms_x, fontsize=10)
ax4.set_ylim(0, max(lab_sum["overall_handshakes_per_second"]) * 1.15)

aplicar_estil_academic(ax4)
plt.tight_layout()
fig4.savefig("results/annex_lab_throughput.png", dpi=300)

# ==========================================
# 4. TAIL LATENCY (Mitjana vs P95 vs P99)
# ==========================================
fig5, ax5 = plt.subplots(figsize=(8, 5))
w = 0.25
m  = lab_sum["overall_mean_handshake_ms"]
p95 = lab_sum["p95_batch_mean_ms"]
p99 = lab_sum["p99_batch_mean_ms"]

# Utilitzem colors genèrics per diferenciar l'estadística (Mitjana, P95, P99) en cada escenari
bm = ax5.bar(x - w, m, w, label="Mitjana", color="#4C72B0", zorder=3)
b95 = ax5.bar(x, p95, w, label="P95", color="#DD8452", zorder=3)
b99 = ax5.bar(x + w, p99, w, label="P99", color="#C44E52", zorder=3)

ax5.bar_label(bm, fmt="%.2f", padding=2, fontsize=8)
ax5.bar_label(b95, fmt="%.2f", padding=2, fontsize=8)
ax5.bar_label(b99, fmt="%.2f", padding=2, fontsize=8)

ax5.set_ylabel("Temps (ms)", fontsize=11, fontweight="bold")
ax5.set_title("Determinisme de CPU: Tail Latency (Entorn LAB)", fontsize=13, fontweight="bold")
ax5.set_xticks(x)
ax5.set_xticklabels(noms_x, fontsize=10)
ax5.legend(loc='upper left', frameon=True, edgecolor='black')

ax5.set_ylim(0, max(p99) * 1.25)

aplicar_estil_academic(ax5)
plt.tight_layout()
fig5.savefig("results/annex_lab_taillatency.png", dpi=300)

print("Tots els gràfics d'estil acadèmic per a l'Annex (LAB) han estat generats a /results!")