import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import numpy as np
import os

def graficar_mapa_calor(cm: np.ndarray, labels: list, output_dir: str, nombre_archivo: str) -> None:

    os.makedirs(output_dir, exist_ok=True)

    n_clases = len(labels)

    # Normalizamos por fila para ver % de acierto por clase
    # así no importa si una clase tiene más muestras que otra
    with np.errstate(divide="ignore", invalid="ignore"):
        cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
        cm_norm = np.nan_to_num(cm_norm)  # por si alguna clase tiene 0 muestras en test

    # Tamaño dinámico según número de clases
    fig_size = max(14, n_clases * 0.6)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))

    sns.heatmap(
        cm_norm,
        ax=ax,
        cmap="Reds",            # rojo más intenso = más aciertos
        vmin=0.0,
        vmax=1.0,
        xticklabels=labels,
        yticklabels=labels,
        linewidths=0.3,
        linecolor="lightgrey",
        cbar_kws={"label": "Proporción de predicciones", "shrink": 0.8},
        annot=n_clases <= 30,   # solo muestra números si hay pocas clases (si no, queda ilegible)
        fmt=".2f" if n_clases <= 30 else "",
    )

    tick_fontsize = max(7, 11 - n_clases // 12)

    ax.set_xlabel("Clase predicha", fontsize=13, labelpad=15, color="black", fontweight="bold")
    ax.set_ylabel("Clase real", fontsize=13, labelpad=15, color="black", fontweight="bold")

    # Rotación 90° en X: más compacta que 45° cuando hay muchas clases
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha="center", fontsize=tick_fontsize)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, va="center", fontsize=tick_fontsize)
    ax.tick_params(axis="x", pad=4)
    ax.tick_params(axis="y", pad=4)

    plt.tight_layout()

    output_path = os.path.join(output_dir, nombre_archivo)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Mapa de calor guardado en: {output_path}")
