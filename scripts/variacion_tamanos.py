import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path


def recopilar_tamanios(escenario_dir: str) -> pd.DataFrame:
    
    escenario_path = Path(escenario_dir)
    registros = []

    page_dirs = sorted(
        [d for d in escenario_path.iterdir() if d.is_dir() and d.name.startswith("page_")],
        key=lambda d: int(d.name.split("_")[1])   # orden numérico, no lexicográfico
    )

    if not page_dirs:
        print(f"No se encontraron carpetas page_X en: {escenario_dir}")
        sys.exit(1)

    for page_dir in page_dirs:
        jpgs = list(page_dir.glob("*.jpg"))
        for jpg in jpgs:
            registros.append({
                "pagina": page_dir.name,
                "pagina_num": int(page_dir.name.split("_")[1]),
                "archivo": jpg.name,
                "bytes": jpg.stat().st_size
            })

    df = pd.DataFrame(registros)
    print(f"{len(page_dirs)} páginas encontradas, {len(df)} imágenes en total.")
    return df


def graficar_boxplot(df: pd.DataFrame, output_path: str) -> None:

    paginas_ordenadas = df.sort_values("pagina_num")["pagina"].unique()
    datos_por_pagina = [df[df["pagina"] == p]["bytes"].values for p in paginas_ordenadas]
    etiquetas = [p.replace("page_", "p") for p in paginas_ordenadas]  # etiquetas cortas

    n = len(paginas_ordenadas)
    fig_width = max(20, n * 0.28)
    fig, ax = plt.subplots(figsize=(fig_width, 7))

    bp = ax.boxplot(
        datos_por_pagina,
        patch_artist=True,
        medianprops=dict(color="crimson", linewidth=1.8),
        flierprops=dict(marker="o", markersize=2, alpha=0.4, color="steelblue"),
        boxprops=dict(facecolor="steelblue", alpha=0.6),
        whiskerprops=dict(color="steelblue"),
        capprops=dict(color="steelblue"),
        widths=0.6,
    )

    ax.set_xticks(range(1, n + 1))
    ax.set_xticklabels(etiquetas, rotation=90, fontsize=7)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1024:.0f} KB"))
    ax.set_xlabel("Página", fontsize=12, labelpad=8)
    ax.set_ylabel("Tamaño imagen (KB)", fontsize=12, labelpad=8)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_xlim(0.5, n + 0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Boxplot guardado en: {output_path}")


def graficar_cv(df: pd.DataFrame, output_path: str) -> None:

    stats = (
        df.groupby(["pagina", "pagina_num"])["bytes"]
        .agg(media="mean", std="std")
        .reset_index()
    )
    stats["cv"] = (stats["std"] / stats["media"] * 100).fillna(0)
    stats = stats.sort_values("pagina_num")

    n = len(stats)
    fig_width = max(20, n * 0.28)
    fig, ax = plt.subplots(figsize=(fig_width, 6))

    colores = ["tomato" if cv > 10 else "steelblue" for cv in stats["cv"]]
    ax.bar(range(n), stats["cv"], color=colores, alpha=0.8, width=0.7)

    ax.axhline(stats["cv"].mean(), color="black", linestyle="--", linewidth=1.2, label=f"Media CV = {stats['cv'].mean():.1f}%")
    ax.set_xticks(range(n))
    ax.set_xticklabels([p.replace("page_", "p") for p in stats["pagina"]], rotation=90, fontsize=7)
    ax.set_xlabel("Página", fontsize=12, labelpad=8)
    ax.set_ylabel("Coeficiente de variación (%)", fontsize=12, labelpad=8)
    ax.set_title("Variabilidad del tamaño de imágenes por página (CV)\nRojo = CV > 10% (páginas más inestables)", fontsize=14, pad=12)
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"CV plot guardado en: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualización de tamaños de imágenes por página")
    parser.add_argument("escenario", help="Ruta al directorio del escenario (ej: escenario1/webFingerprint01)")
    parser.add_argument("--output_dir", "-o", default="output", help="Carpeta de salida para las gráficas")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    nombre_escenario = Path(args.escenario).name

    df = recopilar_tamanios(args.escenario)

    #graficar_boxplot(df, os.path.join(args.output_dir, f"{nombre_escenario}_boxplot_tamanios.png"))
    graficar_cv(df,      os.path.join(args.output_dir, f"{nombre_escenario}_cv_tamanios.png"))
