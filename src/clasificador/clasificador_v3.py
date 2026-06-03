import os
import pandas as pd
import numpy as np
import argparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from graficar_resultados import graficar_mapa_calor
from mapeo_features import nombre_feature

# RandomForestClassifier está implementado sobre la clase DecisionTreeClassifier,
# y este a su vez utiliza el algoritmo CART (Classification and Regression Trees)
# como método base para construir cada árbol
#
# Parámetros replicados del paper original (Brissaud et al. [1]):
#   - n_estimators = 400  (número de árboles)
#   - max_depth    = 50   (profundidad máxima de cada árbol)
#   - Selección de las N features más importantes (criterio Gini)
#     mediante un RF preliminar antes de entrenar el modelo final
#     (paper original usa N=300; configurable via --top_n)

N_ESTIMATORS = 400  # número de árboles en el Random Forest
MAX_DEPTH    = 50   # profundidad máxima de cada árbol


def clasificadorCW(csv_path: str, n_train: int, seed: int, top_n: int) -> dict:
    # ── Carga del CSV ──────────────────────────────────────────────────────────
    # Cada fila contiene una muestra correspondiente a una captura PCAP.
    if not (1 <= n_train <= 99):
        raise ValueError("n_train debe estar entre 1 y 99 (inclusive)")
    if top_n < 1:
        raise ValueError("top_n debe ser >= 1")

    df = pd.read_csv(csv_path)

    # ── División estratificada train / test ────────────────────────────────────
    # Se realiza de forma independiente dentro de cada clase para garantizar
    # que todas las clases estén representadas proporcionalmente en ambos conjuntos.
    train_idx = []
    test_idx  = []

    rng = np.random.default_rng(seed)

    for label, grupo in df.groupby("label"):
        indices = grupo.index.to_numpy().copy()
        rng.shuffle(indices)

        n = len(indices)
        n_train_samples = int(n * n_train / 100)

        train_idx.extend(indices[:n_train_samples])
        test_idx.extend(indices[n_train_samples:])

    df_train = df.loc[train_idx]
    df_test  = df.loc[test_idx]

    # Verificación de que no hay solapamiento entre train y test
    interseccion = len(set(train_idx).intersection(set(test_idx)))
    cont_clases  = df["label"].value_counts().sort_index()

    X_train = df_train.drop(columns=["label"])
    y_train = df_train["label"]
    X_test  = df_test.drop(columns=["label"])
    y_test  = df_test["label"]

    # Ajustamos top_n si supera el número de features disponibles
    n_features_disponibles = X_train.shape[1]
    if top_n > n_features_disponibles:
        print(f" top_n={top_n} supera el número de features disponibles "
              f"({n_features_disponibles}). Se usarán todas.")
        top_n = n_features_disponibles

    # ── Paso 1: RF preliminar para selección de features ──────────────────────
    # Se entrena un primer Random Forest con el conjunto completo de features
    # para calcular la importancia de cada una según el criterio de Gini.
    # A continuación se seleccionan las top_n más importantes.
    print(f"[1/2] Entrenando RF preliminar con {n_features_disponibles} features "
          f"para seleccionar las top {top_n}...")

    clf_pre = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        n_jobs=-1,
        random_state=seed
    )
    clf_pre.fit(X_train, y_train)

    importancias_pre = pd.Series(clf_pre.feature_importances_, index=X_train.columns)
    top_features     = importancias_pre.sort_values(ascending=False).head(top_n).index.tolist()

    print(f"    → {len(top_features)} features seleccionadas.")

    # Reducimos los conjuntos a las features seleccionadas
    X_train_top = X_train[top_features]
    X_test_top  = X_test[top_features]

    # ── Paso 2: RF final con las features seleccionadas ───────────────────────
    print(f"[2/2] Entrenando RF final con {len(top_features)} features...")

    clf = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        n_jobs=-1,
        random_state=seed
    )
    clf.fit(X_train_top, y_train)

    # ── Evaluación ────────────────────────────────────────────────────────────
    y_pred   = clf.predict(X_test_top)
    acc      = accuracy_score(y_test, y_pred)
    aciertos = (y_pred == y_test).sum()

    labels = sorted(y_test.unique())
    cm     = confusion_matrix(y_test, y_pred, labels=labels)

    # ── Top 20 features más importantes del modelo final ─────────────────────
    n_top20 = min(20, len(top_features))
    importancias   = pd.Series(clf.feature_importances_, index=X_train_top.columns)
    top20          = importancias.sort_values(ascending=False).head(n_top20)
    valores_medios = X_test_top.mean()

    tabla_top20 = pd.DataFrame({
        "ranking":     range(1, len(top20) + 1),
        "feature":     top20.index,
        "Valor medio": [valores_medios[f] for f in top20.index],
        "descripcion": [nombre_feature(f) for f in top20.index],
        "importancia": top20.values,
    })

    resultados = {
        "train_shape":              df_train.shape,
        "test_shape":               df_test.shape,
        "interseccion_train_test":  interseccion,
        "cont_clases":              cont_clases,
        "n_features_total":         n_features_disponibles,
        "n_features_seleccionadas": len(top_features),
        "top_features":             top_features,
        "accuracy":                 acc,
        "aciertos":                 aciertos,
        "total_test":               len(y_test),
        "matriz_confusion":         cm,
        "labels":                   labels,
        "tabla_top20_features":     tabla_top20,
        "seed":                     seed,
        "top_n":                    top_n,
    }

    return resultados


def guardar_resultados(resultados: dict, output_path: str) -> None:
    with open(output_path, "w") as f:
        f.write("Resultados del Clasificador Random Forest Closed World\n")
        f.write(f"(Parámetros paper: n_estimators={N_ESTIMATORS}, "
                f"max_depth={MAX_DEPTH}, top_features={resultados['top_n']})\n\n")
        f.write(f"Shape del conjunto de entrenamiento: {resultados['train_shape']}\n")
        f.write(f"Shape del conjunto de test:          {resultados['test_shape']}\n")
        f.write(f"Intersección entre train y test:     {resultados['interseccion_train_test']}\n")
        f.write(f"Semilla utilizada:                   {resultados['seed']}\n")
        f.write(f"Features totales:                    {resultados['n_features_total']}\n")
        f.write(f"Features seleccionadas (top Gini):   {resultados['n_features_seleccionadas']}\n")
        f.write("\nNúmero de muestras por clase:\n")
        f.write(str(resultados["cont_clases"]))
        f.write(f"\n\nAccuracy: {resultados['accuracy']:.4f}\n")
        f.write(f"Aciertos: {resultados['aciertos']} de {resultados['total_test']}\n")
        f.write("\nMatriz de confusión:\n")
        for row in resultados["matriz_confusion"]:
            f.write("  " + " ".join(f"{num:5d}" for num in row) + "\n")
        f.write(f"\nTop {min(20, resultados['top_n'])} features más importantes (modelo final):\n")
        tabla = resultados["tabla_top20_features"]
        f.write(f"{'Rank':<6}{'Feature':<18}{'Descripción':<40}{'Valor medio':<18}{'Importancia':>14}\n")
        f.write("-" * 110 + "\n")
        for _, row in tabla.iterrows():
            f.write(
                f"{row['ranking']:<6} "
                f"{row['feature']:<18} "
                f"{row['descripcion']:<40} "
                f"{row['Valor medio']:<18.4f} "
                f"{row['importancia']:>14.6f}\n"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clasificador Random Forest Closed World — parámetros paper Brissaud et al."
    )
    parser.add_argument("csv", help="Ruta al CSV de features")
    parser.add_argument(
        "--output", "-o",
        default="resultados_clasificador.txt",
        help="Ruta del archivo de salida (.txt)"
    )
    parser.add_argument(
        "--n_train", "-n",
        type=int,
        default=80,
        help="Porcentaje de muestras para entrenamiento (1-99, default=80)"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=42,
        help="Semilla para la aleatorización (default=42)"
    )
    parser.add_argument(
        "--top_n", "-t",
        type=int,
        default=300,
        help="Número de features a seleccionar por importancia Gini (default=300, como en el paper)"
    )

    args = parser.parse_args()

    resultados = clasificadorCW(
        args.csv,
        n_train=args.n_train,
        seed=args.seed,
        top_n=args.top_n
    )

    if args.output:
        guardar_resultados(resultados, args.output)

    graficar_mapa_calor(
        cm=resultados["matriz_confusion"],
        labels=resultados["labels"],
        output_dir=os.path.dirname(args.output),
        nombre_archivo=f"mapa_calor_top{args.top_n}.png"
    )
