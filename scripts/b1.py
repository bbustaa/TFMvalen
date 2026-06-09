#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

DIRECTORIO_SALIDA = r"C:\Users\valeb\Desktop\CIBER\TFMvalen\graficas"

C_GET    = "#1f6feb"   # azul: peticiones GET (C->S)
C_ACK    = "#7aa7e0"   # azul claro: ACK (C->S)
C_SERVER = "#e07b39"   # naranja: datos servidor (S->C)
C_BURST  = "#1f6feb"
C_ZERO   = "#d1495b"
C_AXIS   = "#3a3a3a"
C_TXT    = "#222222"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})

# (x, tipo, bytes)  tipo in {"GET","ACK","S"}
events = [
    (1.0,  "GET", None),
    (1.6,  "GET", None),   # consecutivas, multiplexadas -> ráfaga nula
    (2.2,  "GET", None),   # consecutivas, multiplexadas -> ráfaga nula
    (2.9,  "S", 1300),
    (3.5,  "S", 1300),
    (4.1,  "S", 1300),
    (4.7,  "S", 700),
    (5.4,  "ACK", None),
    (6.0,  "S", 1300),
    (6.6,  "S", 550),
    (7.2,  "ACK", None),
    (7.8,  "GET", None),   # nueva petición -> ráfaga nula con el ACK anterior
    (8.5,  "S", 1300),
    (9.1,  "S", 1300),
    (9.7,  "S", 900),
    (10.6, "ACK", None),
]

client = [(x, t) for (x, t, _) in events if t in ("GET", "ACK")]
client_x = [x for x, _ in client]

# Ráfagas: suma de bytes del servidor entre clientes consecutivos
bursts = []
for i in range(len(client_x) - 1):
    xa, xb = client_x[i], client_x[i + 1]
    val = sum(b for (x, t, b) in events if t == "S" and xa < x < xb)
    bursts.append((xa, xb, val))
burst_values = [b[2] for b in bursts]

fig, ax = plt.subplots(figsize=(13.0, 6.4))
AXIS_Y = 0.0
CLIENT_H = 1.05
SCALE = 1.05 / 1300.0

# Línea temporal
ax.annotate("", xy=(11.3, AXIS_Y), xytext=(0.4, AXIS_Y),
            arrowprops=dict(arrowstyle="-|>", color=C_AXIS, lw=1.8))
ax.text(11.35, AXIS_Y, "tiempo", va="center", ha="left", fontsize=11,
        color=C_AXIS, style="italic")

# Etiquetas de dirección
ax.text(0.05, CLIENT_H + 0.15, r"$C \rightarrow S$", fontsize=15, fontweight="bold",
        color=C_GET, ha="left", va="center")
ax.text(0.05, -1.65, r"$S \rightarrow C$", fontsize=15, fontweight="bold",
        color=C_SERVER, ha="left", va="center")

# Flechas cliente (delimitadores, no se solapan)
for (x, t) in client:
    col = C_GET if t == "GET" else C_ACK
    h = CLIENT_H if t == "GET" else CLIENT_H * 0.78
    ax.annotate("", xy=(x, h), xytext=(x, AXIS_Y),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=2.4))
    ax.text(x, h + 0.08, t, fontsize=7.5, color=col, ha="center", va="bottom",
            fontweight="bold")
    ax.plot([x, x], [AXIS_Y, -1.45], color=col, lw=0.8, ls=(0, (2, 3)), alpha=0.40)

# Flechas servidor (longitud proporcional a bytes)
for (x, t, b) in events:
    if t == "S":
        length = b * SCALE
        ax.annotate("", xy=(x, -length), xytext=(x, AXIS_Y),
                    arrowprops=dict(arrowstyle="-|>", color=C_SERVER, lw=2.4))
        ax.text(x, -length - 0.12, f"{b}", fontsize=8.2, color=C_SERVER,
                ha="center", va="top")

# Cajas de ráfaga
brace_y = CLIENT_H + 0.45
label_y = CLIENT_H + 0.78
sub = ["\u2081", "\u2082", "\u2083", "\u2084", "\u2085", "\u2086", "\u2087"]

for i, (xa, xb, val) in enumerate(bursts):
    is_zero = (val == 0)
    col = C_ZERO if is_zero else C_BURST
    ax.plot([xa, xa, xb, xb], [brace_y - 0.12, brace_y, brace_y, brace_y - 0.12],
            color=col, lw=1.6)
    xc = (xa + xb) / 2
    ax.text(xc, label_y, f"$B{sub[i]}$={val}", fontsize=9.8, color=col,
            ha="center", va="bottom", fontweight="bold")
    if is_zero:
        ax.axvspan(xa, xb, color=C_ZERO, alpha=0.09)


# ----------------------------- Leyenda -----------------------------
legend_elems = [
    Line2D([0], [0], color=C_GET, lw=2.4, marker=">", markersize=7,
           label="Petición GET (C\u2192S)"),
    Line2D([0], [0], color=C_ACK, lw=2.4, marker=">", markersize=7,
           label="ACK (C\u2192S)"),
    Line2D([0], [0], color=C_SERVER, lw=2.4, marker="v", markersize=7,
           label="Registro TLS servidor (S\u2192C)"),
    Line2D([0], [0], color=C_ZERO, lw=1.6, label="Ráfaga nula (Bᵢ = 0)"),
]
ax.legend(handles=legend_elems, loc="upper right", fontsize=8.8, frameon=True,
          framealpha=0.95, edgecolor="#cccccc", bbox_to_anchor=(1.0, 1.03))

ax.set_xlim(-0.1, 12.1)
ax.set_ylim(-3.6, 3.05)
ax.axis("off")
plt.tight_layout()
os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)
ruta_salida = os.path.join(DIRECTORIO_SALIDA, "burst_metodo1.png")
fig.savefig(ruta_salida, dpi=300, bbox_inches="tight")
print(f"Guardado en: {ruta_salida}")