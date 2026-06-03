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

def clasificadorCW(csv_path: str, n_train: int, seed: int) -> dict:
    # bueno lo primero cargar el csv con los features :)
    # cada fila contiene una muestra correspondiente a una captura
    
    # validación del parámetro
    if not (0 <= n_train <= 100):
        raise ValueError("n_train debe estar entre 1 y 99 (inclusive)")
    
    df = pd.read_csv(csv_path)

    # dos listas --> almacenan índices de las muestras que se
    # usarán para entrenar y testear el modelo
    train_idx = []
    test_idx = []

    # para reproducibilidad, fijamos la semilla del generador de números aleatorios
    # esto asegura que cada vez que ejecutemos el código, obtendremos la misma división 
    # entre train y test
    rng = np.random.default_rng(seed)

    # agrupamos el DataFrame por la columna "label", que contiene las clases de cada muestra
    # división independiente dentro de cada clase
    for label, grupo in df.groupby("label"):
        
        # índices de las filas que pertenecen a esa clase --> copia para poder barajear
        indices = grupo.index.to_numpy().copy()
        rng.shuffle(indices)
        
        n = len(indices)
        n_train_samples = int(n * n_train / 100)  # conversión de porcentaje a número de muestras

        train_idx.extend(indices[:n_train_samples])         # primeras n_train_samples muestras para entrenamiento
        test_idx.extend(indices[n_train_samples:])          # resto de muestras para test

    # se construyen los dataframes de train y test usando los índices seleccionados
    df_train = df.loc[train_idx]
    df_test = df.loc[test_idx]

    # comprobación de que no hay solapamiento entre train y test
    train_set = set(train_idx)
    test_set = set(test_idx)
    interseccion = len(train_set.intersection(test_set))
    cont_clases = df["label"].value_counts().sort_index()

    # separamos las características (X) de las etiquetas (y) para ambos conjuntos
    X_train = df_train.drop(columns=["label"])
    y_train = df_train["label"]

    X_test = df_test.drop(columns=["label"])
    y_test = df_test["label"]

    # ENTRENAMIENTO DEL RANDOM FOREST --> conjunto de varios árboles de decisión
    # entrenados con el subconjunto de datos mencionado antes
    clf = RandomForestClassifier(
        n_estimators=100,           # número de árboles en el Random Forest
        n_jobs=-1,                  # usar todos los núcleos disponibles para acelerar el entrenamiento
        random_state=seed           # semilla para reproducibilidad
    )

    # se entrena el modelo con los datos de entrenamiento
    clf.fit(X_train, y_train)

    # se hacen predicciones sobre el conjunto de test
    y_pred = clf.predict(X_test)

    # se calcula la precisión de las predicciones comparándolas con las etiquetas reales
    acc = accuracy_score(y_test, y_pred)
    aciertos = (y_pred == y_test).sum()
    
    # Para ver qé páginas confunde con cuáles
    labels = sorted(y_test.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    
    importancias = pd.Series(clf.feature_importances_, index=X_train.columns)
    top20 = importancias.sort_values(ascending=False).head(20)
    
    # Para mostrar valores medios de los features en el top 20
    valores_medios = X_test.mean()

    tabla_top20 = pd.DataFrame({
        "ranking": range(1, len(top20) + 1),
        "feature": top20.index,
        "Valor medio": [valores_medios[f] for f in top20.index], # valores medios de cada feature en el conjunto de test
        "descripcion": [nombre_feature(f) for f in top20.index],
        "importancia": top20.values,
    })
    
    resultados = {
        "train_shape": df_train.shape,
        "test_shape": df_test.shape,
        "interseccion_train_test": interseccion,
        "cont_clases": cont_clases,
        "accuracy": acc,
        "aciertos": aciertos,
        "total_test": len(y_test),
        "matriz_confusion": cm,
        "labels": labels,
        "tabla_top20_features": tabla_top20,
        "seed": seed
    }
    
    return resultados
        
def guardar_resultados(resultados: dict, output_path: str) -> None:
    with open(output_path, "w") as f:
        f.write("Resultados del Clasificador Random Forest Closed World\n")
        f.write("\n\n")
        f.write(f"Shape del conjunto de entrenamiento: {resultados['train_shape']}\n")
        f.write(f"Shape del conjunto de test: {resultados['test_shape']}\n")
        f.write(f"Intersección entre train y test: {resultados['interseccion_train_test']}\n")
        f.write(f"Semilla utilizada: {resultados['seed']}\n")
        f.write("\nNúmero de muestras por clase:\n")
        f.write(str(resultados["cont_clases"]))
        f.write(f"\nAccuracy: {resultados['accuracy']:.4f}\n")
        f.write(f"Aciertos: {resultados['aciertos']} de {resultados['total_test']}\n")
        f.write("\nMatriz de confusión:\n")
        cm = resultados["matriz_confusion"]
        for row in cm:
            f.write("  " + " ".join(f"{num:5d}" for num in row) + "\n")
        f.write("\nTop 20 features más importantes:\n")
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
    parser = argparse.ArgumentParser(description="Clasificador Random Forest Closed World")

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

    args = parser.parse_args()

    resultados = clasificadorCW(args.csv, n_train=args.n_train, seed=args.seed)
    if args.output:
        guardar_resultados(resultados, args.output)
        
    graficar_mapa_calor(
        cm=resultados["matriz_confusion"],
        labels=resultados["labels"],
        output_dir=os.path.dirname(args.output),
        nombre_archivo="mapa_calor.png"
    )
