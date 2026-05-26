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
        key=lambda d: int(d.name.split("_")[1])
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


def graficar_boxplot(df: pd.DataFrame, output_path: str, paginas_por_grupo: int = 20) -> None:
    paginas_ordenadas = df.sort_values("pagina_num")["pagina"].unique()
    n_total = len(paginas_ordenadas)
    grupos = [paginas_ordenadas[i:i + paginas_por_grupo]
              for i in range(0, n_total, paginas_por_grupo)]
    n_grupos = len(grupos)

    fig, axes = plt.subplots(n_grupos, 1, figsize=(18, 5 * n_grupos))
    if n_grupos == 1:
        axes = [axes]

    for ax, grupo in zip(axes, grupos):
        datos = [df[df["pagina"] == p]["bytes"].values for p in grupo]
        etiquetas = [p.replace("page_", "p") for p in grupo]
        n = len(grupo)

        ax.boxplot(
            datos,
            patch_artist=True,
            medianprops=dict(color="crimson", linewidth=1.8),
            flierprops=dict(marker="o", markersize=2, alpha=0.4, color="steelblue"),
            boxprops=dict(facecolor="steelblue", alpha=0.6),
            whiskerprops=dict(color="steelblue"),
            capprops=dict(color="steelblue"),
            widths=0.6,
        )
        ax.set_xticks(range(1, n + 1))
        ax.set_xticklabels(etiquetas, rotation=45, fontsize=9, ha="right")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1024:.0f} KB"))
        ax.set_ylabel("Tamaño imagen (KB)", fontsize=11)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.set_xlim(0.5, n + 0.5)

    axes[0].set_title("Distribución del tamaño de imágenes por página (boxplot)", fontsize=14, pad=12)
    axes[-1].set_xlabel("Página", fontsize=12, labelpad=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Boxplot guardado en: {output_path}")


def graficar_cv(df: pd.DataFrame, output_path: str, paginas_por_grupo: int = 20) -> None:
    stats = (
        df.groupby(["pagina", "pagina_num"])["bytes"]
        .agg(media="mean", std="std")
        .reset_index()
    )
    stats["cv"] = (stats["std"] / stats["media"] * 100).fillna(0)
    stats = stats.sort_values("pagina_num")

    paginas_ordenadas = stats["pagina"].values
    n_total = len(paginas_ordenadas)
    grupos_idx = [list(range(i, min(i + paginas_por_grupo, n_total)))
                  for i in range(0, n_total, paginas_por_grupo)]
    n_grupos = len(grupos_idx)

    fig, axes = plt.subplots(n_grupos, 1, figsize=(18, 5 * n_grupos))
    if n_grupos == 1:
        axes = [axes]

    media_global = stats["cv"].mean()

    for ax, idxs in zip(axes, grupos_idx):
        grupo = stats.iloc[idxs]
        colores = ["tomato" if cv > 10 else "steelblue" for cv in grupo["cv"]]
        ax.bar(range(len(grupo)), grupo["cv"], color=colores, alpha=0.8, width=0.7)
        ax.axhline(media_global, color="black", linestyle="--", linewidth=1.2,
                   label=f"Media CV global = {media_global:.1f}%")
        ax.set_xticks(range(len(grupo)))
        ax.set_xticklabels(
            [p.replace("page_", "p") for p in grupo["pagina"]],
            rotation=45, fontsize=9, ha="right"
        )
        ax.set_ylabel("CV (%)", fontsize=11)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.legend(fontsize=9)

    axes[0].set_title(
        "Variabilidad del tamaño de imágenes por página (CV)\nRojo = CV > 10% (páginas más inestables)",
        fontsize=14, pad=12
    )
    axes[-1].set_xlabel("Página", fontsize=12, labelpad=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"CV plot guardado en: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualización de tamaños de imágenes por página")
    parser.add_argument("escenario", help="Ruta al directorio del escenario (ej: escenario1/webFingerprint01)")
    parser.add_argument("--output_dir", "-o", default="output",
                        help="Carpeta de salida para las gráficas")
    parser.add_argument("--nombre", "-n", default=None,
                        help="Nombre base para los ficheros de salida (sin extensión). "
                             "Por defecto usa el nombre del directorio del escenario.")
    parser.add_argument("--tipo", "-t", choices=["boxplot", "cv", "ambos"], default="ambos",
                        help="Tipo de gráfica a generar: boxplot, cv, o ambos (por defecto)")
    parser.add_argument("--por_grupo", "-g", type=int, default=20,
                        help="Número de páginas por subplot (por defecto 20)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    nombre_base = args.nombre if args.nombre else Path(args.escenario).name

    df = recopilar_tamanios(args.escenario)

    if args.tipo in ("boxplot", "ambos"):
        out_boxplot = os.path.join(args.output_dir, f"{nombre_base}_boxplot.png")
        graficar_boxplot(df, out_boxplot, paginas_por_grupo=args.por_grupo)

    if args.tipo in ("cv", "ambos"):
        out_cv = os.path.join(args.output_dir, f"{nombre_base}_cv.png")
        graficar_cv(df, out_cv, paginas_por_grupo=args.por_grupo)
