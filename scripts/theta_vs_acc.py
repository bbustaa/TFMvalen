import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

DIRECTORIO_SALIDA = r"C:\Users\valeb\Desktop\CIBER\TFMvalen\graficas\escenario4"  
NOMBRE_FICHERO    = "theta_vs_accuracy.png"

# Eje X: número de características
top_n = [1, 2, 3, 5, 10]

# Eje Y izquierdo: pares solapados (Θ)
theta = [228, 106, 80, 32, 16]

# Eje Y derecho: accuracy
accuracy = [0.5531, 0.8984, 0.9617, 0.9906, 0.9930]

COLOR_THETA   = '#c0392b'   # rojo para Θ
COLOR_ACC     = '#27ae60'   # verde para accuracy
LINEWIDTH     = 2.5
FONTSIZE_EJES = 13
FONTSIZE_TICK = 11
DPI           = 200
FIGSIZE       = (9, 5.5)    # ancho x alto en pulgadas

# Escala del eje Θ: 'linear' o 'log'
ESCALA_THETA  = 'linear'

fig, ax1 = plt.subplots(figsize=FIGSIZE)
fig.patch.set_facecolor('white')

# Eje izquierdo: Θ
ax1.set_xlabel('Número de características (top N)', fontsize=FONTSIZE_EJES, color='#111')
ax1.set_ylabel('Θ  (pares solapados)', fontsize=FONTSIZE_EJES, color=COLOR_THETA)
ax1.plot(top_n, theta,
         color=COLOR_THETA, linewidth=LINEWIDTH,
         zorder=3)
ax1.set_yscale(ESCALA_THETA)
ax1.tick_params(axis='y', labelcolor=COLOR_THETA, labelsize=FONTSIZE_TICK)
ax1.tick_params(axis='x', labelsize=FONTSIZE_TICK, colors='#111')
ax1.set_xticks(top_n)
ax1.spines['left'].set_color(COLOR_THETA)
ax1.spines['left'].set_linewidth(1.4)
ax1.spines['bottom'].set_color('#333')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.grid(axis='y', color='#dddddd', linewidth=0.7, linestyle='--', zorder=0)

# Eje derecho: accuracy
ax2 = ax1.twinx()
ax2.set_ylabel('Accuracy', fontsize=FONTSIZE_EJES, color=COLOR_ACC)
ax2.plot(top_n, accuracy,
         color=COLOR_ACC, linewidth=LINEWIDTH,
         zorder=3)
ax2.tick_params(axis='y', labelcolor=COLOR_ACC, labelsize=FONTSIZE_TICK)
ax2.set_ylim(0, 1.08)
ax2.yaxis.set_major_formatter(
    ticker.FuncFormatter(lambda v, _: f'{v:.2f}'))
ax2.spines['right'].set_color(COLOR_ACC)
ax2.spines['right'].set_linewidth(1.4)
ax2.spines['top'].set_visible(False)
ax2.spines['left'].set_visible(False)

plt.tight_layout()
ruta_salida = os.path.join(DIRECTORIO_SALIDA, NOMBRE_FICHERO)
plt.savefig(ruta_salida, dpi=DPI, bbox_inches='tight', facecolor='white')
print(f"Guardado en: {ruta_salida}")