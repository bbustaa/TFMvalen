import argparse
import os
import pandas as pd


def filtrar_csv(csv_entrada: str, csv_salida: str, features: list[str]) -> None:
    df = pd.read_csv(csv_entrada)

    if "label" not in df.columns:
        raise ValueError("El CSV no contiene la columna 'label'.")

    columnas = ["label"] + features

    columnas_no_encontradas = [c for c in columnas if c not in df.columns]
    if columnas_no_encontradas:
        raise ValueError(
            f"Estas columnas no existen en el CSV: {columnas_no_encontradas}"
        )

    df_filtrado = df[columnas]
    df_filtrado.to_csv(csv_salida, index=False)

    print(f"[OK] CSV filtrado guardado en: {csv_salida}")
    print(f"Columnas guardadas: {columnas}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filtrar un CSV conservando label y las features indicadas"
    )
    parser.add_argument("csv_entrada", help="Ruta del CSV original")
    parser.add_argument(
        "--features",
        "-f",
        nargs="+",
        required=True,
        help="Lista de features a conservar, por ejemplo: feature_2 feature_18564"
    )
    parser.add_argument(
        "--salida",
        "-o",
        default="csv_filtrado.csv",
        help="Ruta del CSV filtrado de salida"
    )

    args = parser.parse_args()

    filtrar_csv(args.csv_entrada, args.salida, args.features)
