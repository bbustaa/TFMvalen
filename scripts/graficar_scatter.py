import os
import argparse
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D


def cargar_datos(csv_path: str, features: list[str]) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    for f in features:
        if f not in df.columns:
            raise ValueError(f"El feature '{f}' no existe en el CSV.")
    return df


def graficar_scatter_matrix(df: pd.DataFrame, features: list[str], output_dir: str) -> None:

    paginas = sorted(df["label"].unique(), key=lambda x: int(x.split("_")[1]))
    n_paginas = len(paginas)

    pagina_a_idx = {p: i for i, p in enumerate(paginas)}
    color_idx    = df["label"].map(pagina_a_idx).values
    cmap         = matplotlib.colormaps.get_cmap("tab20")
    colores_filas = cmap(color_idx / n_paginas)

    n = len(features)
    fig, axes = plt.subplots(n, n, figsize=(16, 16))
    fig.suptitle(
        f"Scatter matrix — Top 3 features\n{features[0]}  ·  {features[1]}  ·  {features[2]}",
        fontsize=14, fontweight="bold", y=1.01
    )

    for row in range(n):
        for col in range(n):
            ax = axes[row][col]
            if row == col:
                for p in paginas:
                    mask = df["label"] == p
                    ax.hist(
                        df.loc[mask, features[row]].values,
                        bins=15,
                        color=cmap(pagina_a_idx[p] / n_paginas),
                        alpha=0.4,
                        density=True
                    )
                ax.set_xlabel(features[row], fontsize=8)
                ax.set_ylabel("Densidad", fontsize=8)
            else:
                ax.scatter(
                    df[features[col]].values,
                    df[features[row]].values,
                    c=colores_filas,
                    alpha=0.5,
                    s=12,
                    linewidths=0
                )
                ax.set_xlabel(features[col], fontsize=8)
                ax.set_ylabel(features[row], fontsize=8)

            ax.tick_params(labelsize=7)
            ax.grid(linestyle="--", alpha=0.3)

    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=cmap(pagina_a_idx[p] / n_paginas),
                   markersize=5, label=p.replace("pagina_", "p"))
        for p in paginas
    ]
    fig.legend(
        handles=handles, loc="center right", bbox_to_anchor=(1.12, 0.5),
        fontsize=6, ncol=2, title="Páginas", title_fontsize=8, framealpha=0.7
    )

    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, "scatter_matrix_top3.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[OK] Scatter matrix guardado en: {out}")


def graficar_scatter_3d(df: pd.DataFrame, features: list[str], output_dir: str) -> None:

    paginas = sorted(df["label"].unique(), key=lambda x: int(x.split("_")[1]))
    n_paginas = len(paginas)

    pagina_a_idx  = {p: i for i, p in enumerate(paginas)}
    color_idx     = df["label"].map(pagina_a_idx).values
    cmap          = matplotlib.colormaps.get_cmap("tab20")
    colores_filas = cmap(color_idx / n_paginas)

    vistas = [
        (20,  30,  "Vista frontal-derecha"),
        (20,  120, "Vista frontal-izquierda"),
        (60,  30,  "Vista superior"),
        (10,  200, "Vista posterior"),
    ]

    fig = plt.figure(figsize=(20, 18))
    fig.suptitle(
        f"Scatter 3D — Top 3 features\nX: {features[0]}  ·  Y: {features[1]}  ·  Z: {features[2]}",
        fontsize=14, fontweight="bold"
    )

    x = df[features[0]].values
    y = df[features[1]].values
    z = df[features[2]].values

    for idx, (elev, azim, titulo) in enumerate(vistas):
        ax = fig.add_subplot(2, 2, idx + 1, projection="3d")
        ax.scatter(x, y, z, c=colores_filas, alpha=0.6, s=15, linewidths=0)
        ax.set_xlabel(features[0], fontsize=8, labelpad=6)
        ax.set_ylabel(features[1], fontsize=8, labelpad=6)
        ax.set_zlabel(features[2], fontsize=8, labelpad=6)
        ax.set_title(titulo, fontsize=10)
        ax.view_init(elev=elev, azim=azim)
        ax.tick_params(labelsize=6)

    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=cmap(pagina_a_idx[p] / n_paginas),
                   markersize=5, label=p.replace("pagina_", "p"))
        for p in paginas
    ]
    fig.legend(
        handles=handles, loc="center right", bbox_to_anchor=(1.1, 0.5),
        fontsize=6, ncol=2, title="Páginas", title_fontsize=8, framealpha=0.7
    )

    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, "scatter_3d_top3.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[OK] Scatter 3D guardado en: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scatter matrix y 3D de los top 3 features")
    parser.add_argument("csv",              help="Ruta al CSV de features")
    parser.add_argument("feature0",         help="Primer feature  (ej: feature_2)")
    parser.add_argument("feature1",         help="Segundo feature (ej: feature_18564)")
    parser.add_argument("feature2",         help="Tercer feature  (ej: feature_18565)")
    parser.add_argument("--output_dir", "-o", default="output", help="Carpeta de salida")
    args = parser.parse_args()

    features = [args.feature0, args.feature1, args.feature2]
    df = cargar_datos(args.csv, features)

    graficar_scatter_matrix(df, features, args.output_dir)
    graficar_scatter_3d(df, features, args.output_dir)
