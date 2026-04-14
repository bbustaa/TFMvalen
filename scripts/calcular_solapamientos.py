import os
import argparse
import pandas as pd
from itertools import combinations

def calcular_solapamientos(df: pd.DataFrame, feature: str, tolerancia: float) -> dict:

    paginas = df["label"].unique()
    solapamientos = {}
    
    valores_por_pagina = {p: set(df[df["label"] == p][feature].values) for p in paginas}
    
    for pa, pb in combinations(sorted(paginas), 2):
        va = valores_por_pagina[pa]
        vb = valores_por_pagina[pb]
        
        if tolerancia == 0.0:
            coincidencias = len(va.intersection(vb))
        else:
            coincidencias = sum(
                1 for a in va
                for b in vb
                if abs(a - b) <= tolerancia
            )
        
        if coincidencias > 0:
            solapamientos[(pa, pb)] = coincidencias
    
    return solapamientos

def guardar_resultados(feature: str, tolerancia: float, csv_path: str, output_dir: str) -> None:
    
    df = pd.read_csv(csv_path)
    
    print("Calculando solapamientos :)")
    solapamientos = calcular_solapamientos(df, feature, tolerancia)
    total_solapamientos = sum(solapamientos.values())
    pares_con_solape = len(solapamientos)
    
    txt_path = os.path.join(output_dir, f"solapamientos_{feature}.txt")
    with open(txt_path, "w") as f:
        f.write(f"Resumen de solapamientos — Feature: {feature}\n")
        f.write(f"Tolerancia: {tolerancia}\n")
        f.write(f"Total coincidencias: {total_solapamientos}\n")
        f.write(f"Pares de páginas con solapamiento: {pares_con_solape}\n\n")
        f.write(f"{'Par de páginas':<40} {'Solapamientos':>14}\n")
        f.write("-" * 56 + "\n")
        for (pa, pb), n in sorted(solapamientos.items(), key=lambda x: -x[1]):
            f.write(f"{pa} <-> {pb:<25} {n:>14}\n")
    print(f"Resultados guardados en: {txt_path}")

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
    
    guardar_resultados(args.feature, args.tolerancia, args.csv, args.output_dir)