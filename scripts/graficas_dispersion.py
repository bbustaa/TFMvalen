import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from calcular_solapamientos import calcular_solapamientos, guardar_resultados

def graficar_boxplot_feature(csv_path: str, feature: str, output_dir: str) -> None:
    
    df = pd.read_csv(csv_path)
    
    if feature not in df.columns:
        raise ValueError(f"El feature '{feature}' no existe en el CSV.")
    
    paginas_todas = sorted(df["label"].unique(), key=lambda x: int(x.split("_")[1]))
    n_paginas = len(paginas_todas)
    chunk_size = 10
    grupos = [paginas_todas[i:i+chunk_size] for i in range(0, n_paginas, chunk_size)]
    n_grupos = len(grupos)

    solapamientos = calcular_solapamientos(df, feature, tolerancia=0.0)
    total_solapamientos = sum(solapamientos.values())
    pares_con_solape = len(solapamientos)

    fig, axes = plt.subplots(n_grupos, 1, figsize=(20, 5 * n_grupos))
    fig.suptitle(
        f"Distribución del feature: {feature}\n"
        f"Solapamientos totales: {total_solapamientos}  |  Pares solapados: {pares_con_solape}",
        fontsize=15, fontweight="bold", y=1.001
    )

    if n_grupos == 1:
        axes = [axes]

    cmap = plt.get_cmap("tab20")

    for g_idx, (ax, grupo) in enumerate(zip(axes, grupos)):
        datos = [df[df["label"] == p][feature].values for p in grupo]
        etiquetas = [p.replace("pagina_", "p").replace("page_", "p") for p in grupo]
        colores = [cmap(i % 20) for i in range(len(grupo))]

        bp = ax.boxplot(
            datos,
            patch_artist=True,
            medianprops=dict(color="crimson", linewidth=2),
            flierprops=dict(marker="o", markersize=3, alpha=0.4),
            whiskerprops=dict(linewidth=1.2),
            capprops=dict(linewidth=1.2),
            widths=0.6,
        )

        for patch, color in zip(bp["boxes"], colores):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        # solapamientos de este grupo
        paginas_grupo_set = set(grupo)
        solapes_grupo = {
            k: v for k, v in solapamientos.items()
            if k[0] in paginas_grupo_set and k[1] in paginas_grupo_set
        }

        rango_inicio = grupo[0].split("_")[1]
        rango_fin = grupo[-1].split("_")[1]
        solape_texto = f"Solapamientos: {sum(solapes_grupo.values())} ({len(solapes_grupo)} pares)"
        ax.set_title(f"Páginas {rango_inicio}–{rango_fin}  |  {solape_texto}", fontsize=12)
        ax.set_xticks(range(1, len(grupo) + 1))
        ax.set_xticklabels(etiquetas, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel(f"Valor de {feature}", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"boxplot_{feature}.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Guardado en: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispersión de un feature por página web")
    parser.add_argument("csv",            help="Ruta al CSV de features")
    parser.add_argument("feature",        help="Nombre del feature a graficar (ej: feature_6)")
    parser.add_argument("--output_dir", "-o", default="output", help="Carpeta de salida")
    parser.add_argument(
        "--tolerancia", "-t",
        type=float,
        default=0.0,
        help="Tolerancia para considerar dos valores como 'solapados' (default=0.0 = exactos)"
    )
    args = parser.parse_args()
    
    graficar_boxplot_feature(args.csv, args.feature, args.output_dir)
    guardar_resultados(args.feature, args.tolerancia, args.csv, args.output_dir)