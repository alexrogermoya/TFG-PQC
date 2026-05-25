import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read the file
df = pd.read_csv("results/handshake_message_sizes.csv")

# Separate by environment
lab   = df[df["environment"] == "lab"]
nginx = df[df["environment"] == "nginx"]

# --- Bar positioning ---
scenarios_lab   = lab["scenario"].tolist()      # ["classic", "hybrid", "pq"]
scenarios_nginx = nginx["scenario"].tolist()    # ["classic", "hybrid"]

all_scenarios = ["classic", "hybrid", "pq"]    # fixed order for x-axis
x     = np.arange(len(all_scenarios))
width = 0.35

# Map values to fixed positions
lab_values   = lab.set_index("scenario").reindex(all_scenarios)["total_handshake_message_bytes"]
nginx_values = nginx.set_index("scenario").reindex(all_scenarios)["total_handshake_message_bytes"]

fig, ax = plt.subplots(figsize=(7, 4))

bars_lab   = ax.bar(x - width/2, lab_values,   width, label="Lab",   color="#4C72B0")
bars_nginx = ax.bar(x + width/2, nginx_values, width, label="Nginx", color="#DD8452")

# --- Formatting ---
ax.set_xlabel("Scenario", fontsize=12)
ax.set_ylabel("Mean Handshake Time (bytes)", fontsize=12)
ax.set_title("Handshake Message Size by Environment and Scenario", fontsize=13, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(["Classic", "Hybrid", "PQ"], fontsize=11)
ax.legend(fontsize=11)
ax.yaxis.grid(True, linestyle="--", alpha=0.7)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig("handshake_size.png", dpi=300)
plt.show()