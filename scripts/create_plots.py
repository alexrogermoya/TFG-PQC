import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# 1. Definim els perfils evolutius (SENSE LOCAL)
perfils_wan = [
    ("wan_regional", "Regional\n(40 ms)"),
    ("wan_interregional", "Interregional\n(120 ms)"),
    ("wan_intercontinental", "Intercontinental\n(250 ms)")
]

etiquetes_x_wan = []
mean_classic, mean_hybrid, mean_pq = [], [], []
tp_classic, tp_hybrid, tp_pq = [], [], []
p99_classic, p99_hybrid, p99_pq = [], [], []

for nom_arxiu, etiqueta in perfils_wan:
    ruta = f"results/handshake_summary_all_{nom_arxiu}.csv"
    if not os.path.exists(ruta):
        print(f"[ERROR] No trobo {ruta}.")
        exit(1)
    df = pd.read_csv(ruta)
    nginx = df[df["environment"] == "nginx"].set_index("scenario")
    
    etiquetes_x_wan.append(etiqueta)
    
    mean_classic.append(nginx.loc["classic", "overall_mean_handshake_ms"])
    mean_hybrid.append(nginx.loc["hybrid", "overall_mean_handshake_ms"])
    mean_pq.append(nginx.loc["pq", "overall_mean_handshake_ms"])
    
    tp_classic.append(nginx.loc["classic", "overall_handshakes_per_second"])
    tp_hybrid.append(nginx.loc["hybrid", "overall_handshakes_per_second"])
    tp_pq.append(nginx.loc["pq", "overall_handshakes_per_second"])
    
    p99_classic.append(nginx.loc["classic", "p99_batch_mean_ms"])
    p99_hybrid.append(nginx.loc["hybrid", "p99_batch_mean_ms"])
    p99_pq.append(nginx.loc["pq", "p99_batch_mean_ms"])

# 2. Dades de mida (La mida és igual a tot arreu, agafem un CSV qualsevol)
df_siz = pd.read_csv("results/handshake_message_sizes_all_wan_regional.csv")
nginx_siz = df_siz[df_siz["environment"] == "nginx"].set_index("scenario")

# Colors professionals
color_classic = "#4C72B0" 
color_hybrid = "#DD8452"  
color_pq = "#55A868"      
color_danger = "#C44E52"

def aplicar_estil_academic(ax):
    """Funció d'estil: Manté l'eix esquerre i inferior (format L), treu el de dalt i la dreta."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # Activem la quadrícula transversal per darrere de les dades
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)


# ==========================================================
# GRÀFIC 1: Direccionalitat (NGINX)
# ==========================================================
fig2, ax2 = plt.subplots(figsize=(7, 5))
x_siz = np.arange(3)
noms_siz = ["Clàssic\n(X25519)", "Híbrid\n(X25519+ML-KEM)", "PQ Pur\n(ML-KEM)"]

c2s = [
    nginx_siz.loc["classic", "client_to_server_bytes"], 
    nginx_siz.loc["hybrid", "client_to_server_bytes"],
    nginx_siz.loc["pq", "client_to_server_bytes"]
]
s2c = [
    nginx_siz.loc["classic", "server_to_client_bytes"], 
    nginx_siz.loc["hybrid", "server_to_client_bytes"],
    nginx_siz.loc["pq", "server_to_client_bytes"]
]
p1 = ax2.bar(x_siz, c2s, 0.5, label='Client -> Servidor', color="#854FBE", zorder=3)
p2 = ax2.bar(x_siz, s2c, 0.5, bottom=c2s, label='Servidor -> Client', color='#C44E52', zorder=3)
for i, total in enumerate(np.add(c2s, s2c)):
    ax2.text(x_siz[i], total + 50, f"{int(total)} B", ha='center', fontweight='bold')
ax2.set_ylabel("Bytes", fontsize=11, fontweight="bold")
ax2.set_title("Trànsit direccional (Entorn NGINX)", fontsize=13, fontweight="bold")
ax2.axhline(y=1500, color="#31AE44", linestyle='-.', label='Límit MTU (~1500 B)', zorder=4)
ax2.set_xticks(x_siz)
ax2.set_xticklabels(noms_siz, fontsize=11)
ax2.legend(frameon=True, edgecolor='black')

aplicar_estil_academic(ax2)
plt.tight_layout()
fig2.savefig("results/plot_main_nginx_directional.png", dpi=300)

# ==========================================================
# FUNCIÓ PELS GRÀFICS EVOLUTIUS WAN (Escala lineal normal)
# ==========================================================
x_wan = np.arange(len(etiquetes_x_wan))
width = 0.25 # Més estret per acomodar les 3 barres

def crear_grafic_wan(dades_classic, dades_hybrid, dades_pq, titol, ylabel, arxiu, format_etiqueta, leg_loc='best'):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    b_cl = ax.bar(x_wan - width, dades_classic, width, label="Clàssic (X25519)", color=color_classic, zorder=3)
    b_hy = ax.bar(x_wan, dades_hybrid, width, label="Híbrid (X25519+ML-KEM)", color=color_hybrid, zorder=3)
    b_pq = ax.bar(x_wan + width, dades_pq, width, label="PQ Pur (ML-KEM)", color=color_pq, zorder=3)

    ax.bar_label(b_cl, fmt=format_etiqueta, padding=3, fontsize=9)
    ax.bar_label(b_hy, fmt=format_etiqueta, padding=3, fontsize=9)
    ax.bar_label(b_pq, fmt=format_etiqueta, padding=3, fontsize=9)
    
    ax.set_xlabel("Distància simulada per WAN", fontsize=11, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=11, fontweight="bold")
    ax.set_title(titol, fontsize=14, fontweight="bold")
    ax.set_xticks(x_wan)
    ax.set_xticklabels(etiquetes_x_wan, fontsize=10)
    ax.legend(loc=leg_loc, frameon=True, edgecolor='black')
    
    # Afegim un 25% més d'espai a dalt perquè les etiquetes no xoquin amb la llegenda
    ax.set_ylim(0, max(max(dades_classic), max(dades_hybrid), max(dades_pq)) * 1.25)
    
    aplicar_estil_academic(ax)
    plt.tight_layout()
    fig.savefig(f"results/{arxiu}", dpi=300)

# GRÀFIC 2: Temps (Mitjana)
crear_grafic_wan(mean_classic, mean_hybrid, mean_pq, "Temps de handshake (Mitjana) - Entorn NGINX", 
                 "Temps (ms)", "plot_main_nginx_time.png", "%.0f ms", leg_loc="upper left")

# GRÀFIC 3: Throughput
crear_grafic_wan(tp_classic, tp_hybrid, tp_pq, "Capacitat del servidor (Throughput) - Entorn NGINX", 
                 "Connexions/segon", "plot_main_nginx_throughput.png", "%.1f", leg_loc="upper right")

# GRÀFIC 4: Tail Latency P99
crear_grafic_wan(p99_classic, p99_hybrid, p99_pq, "Tail Latency P99 - Entorn NGINX", 
                 "Temps P99 (ms)", "plot_main_nginx_taillatency.png", "%.0f ms", leg_loc="upper left")

print("-> Generats els 5 gràfics WAN (amb PQ pur) a /results!")