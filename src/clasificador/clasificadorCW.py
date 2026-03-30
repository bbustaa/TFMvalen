import pandas as pd
import numpy as np
import argparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

# RandomForestClassifier está implementado sobre la clase DecisionTreeClassifier, 
# y este a su vez utiliza el algoritmo CART (Classification and Regression Trees) 
# como método base para construir cada árbol

def clasificadorCW(csv_path: str) -> dict:
    # bueno lo primero cargar el csv con los features :)
    # cada fila contiene una muestra correspondiente a una captura
    df = pd.read_csv(csv_path)

    # dos listas --> almacenan índices de las muestras que se
    # usarán para entrenar y testear el modelo
    train_idx = []
    test_idx = []

    # para reproducibilidad, fijamos la semilla del generador de números aleatorios
    # esto asegura que cada vez que ejecutemos el código, obtendremos la misma división 
    # entre train y test
    rng = np.random.default_rng(42)

    # agrupamos el DataFrame por la columna "label", que contiene las clases de cada muestra
    # división independiente dentro de cada clase
    for label, grupo in df.groupby("label"):
        
        # índices de las filas que pertenecen a esa clase --> copia para poder barajear
        indices = grupo.index.to_numpy().copy()
        rng.shuffle(indices)
        
        n = len(indices)
        n_train = int(n * 0.8)  # 80% para train, 20% para test

        train_idx.extend(indices[:n_train])          # primeros 80% para train
        test_idx.extend(indices[n_train:])           # últimos 20% para test

    # se construyen los dataframes de train y test usando los índices seleccionados
    df_train = df.loc[train_idx]
    df_test = df.loc[test_idx]

    # se muestra el número de muestras en cada conjunto --> mas que todo para comprobar
    # que se está haciendo bien :)
    #print("Train:", df_train.shape)
    #print("Test:", df_test.shape)

    # comprobación de que no hay solapamiento entre train y test
    train_set = set(train_idx)
    test_set = set(test_idx)
    interseccion = len(train_set.intersection(test_set))
    cont_clases = df["label"].value_counts().sort_index()

    #print("Intersección train/test:", len(train_set.intersection(test_set)))    # intersecciòn debe ser 0 --> en caso contrario --> fuga de info
    #print("\nNúmero de muestras por clase:")                                    # nùmero de muestras por por clase en el dataset --> todas las pàginas deben tener el mismo nùmero                           
    #print(df["label"].value_counts().sort_index())

    # separamos las características (X) de las etiquetas (y) para ambos conjuntos
    X_train = df_train.drop(columns=["label"])
    y_train = df_train["label"]

    X_test = df_test.drop(columns=["label"])
    y_test = df_test["label"]

    # ENTRENAMIENTO DEL RANDOM FOREST --> conjunto de varios árboles de decisión
    # entrenados con el subconjunto de datos mencionado antes
    clf = RandomForestClassifier(
        n_estimators=100,           # número de árboles en el bosque --> 100 páginas conocidas :)
        n_jobs=-1,                  # usar todos los núcleos disponibles para acelerar el entrenamiento
        random_state=42             # semilla para reproducibilidad
    )

    # se entrena el modelo con los datos de entrenamiento
    clf.fit(X_train, y_train)

    # se hacen predicciones sobre el conjunto de test
    y_pred = clf.predict(X_test)

    # se calcula la precisión de las predicciones comparándolas con las etiquetas reales
    acc = accuracy_score(y_test, y_pred)
    aciertos = (y_pred == y_test).sum()
    #print("\nResultado OG")
    #print("Accuracy:", acc)
    #print("Aciertos:", (y_pred == y_test).sum(), "de", len(y_test))
    
    # Para ver qé páginas confunde con cuáles
    labels = sorted(y_test.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    
    #print("\nMatriz de confusión:")
    #print(cm)                           # digonales = aciertos, fuera de diagonal = errores
    
    importancias = pd.Series(clf.feature_importances_, index=X_train.columns)
    top20 = importancias.sort_values(ascending=False).head(20)

    #print("\nTop 20 features más importantes:")
    #print(top20)

    # PRUEBA CON LABELS BARAJADAS --> para comprobar que el modelo no está memorizando las etiquetas
    # ESTO PORQUE ME DABA ACCURACY DEL 100% Y ME PARECÌA MUY PERFECTO Y ME DIJO CHATI QUE PODÍA
    # PROBAR A BARAJAR LAS ETIQUETAS PARA VER SI EL MODELO SIGUE OBTENIENDO UN ALTO ACCURACY --> 
    # SI OBTIENE UN ALTO ACCURACY CON LAS ETIQUETAS BARAJADAS, SIGNIFICA QUE EL MODELO ESTÁ MEMORIZANDO 
    # LAS ETIQUETAS EN LUGAR DE APRENDER A GENERALIZAR A PARTIR DE LOS FEATURES
    X_train_reset = X_train.reset_index(drop=True)
    y_train_shuffle = y_train.sample(frac=1, random_state=123).reset_index(drop=True)

    clf_shuffle = RandomForestClassifier(
        n_estimators=100,
        n_jobs=-1,
        random_state=42
    )

    clf_shuffle.fit(X_train_reset, y_train_shuffle)
    y_pred_shuffle = clf_shuffle.predict(X_test)

    acc_shuffle = accuracy_score(y_test, y_pred_shuffle)
    aciertos_shuffle = (y_pred_shuffle == y_test).sum()

    #print("\nPrueba barajeada (?)")
    #print("Accuracy con labels barajadas:", acc_shuffle)
    #print("Aciertos con labels barajadas:", (y_pred_shuffle == y_test).sum(), "de", len(y_test))
    
    resultados = {
        "train_shape": df_train.shape,
        "test_shape": df_test.shape,
        "interseccion_train_test": interseccion,
        "cont_clases": cont_clases,
        "accuracy": acc,
        "aciertos": aciertos,
        "total_test": len(y_test),
        "matriz_confusion": cm,
        "top20_features": top20,
        "accuracy_shuffle": acc_shuffle,
        "aciertos_shuffle": aciertos_shuffle,
    }
    
    return resultados
        
def guardar_resultados(resultados: dict, output_path: str) -> None:
    with open(output_path, "w") as f:
        f.write("Resultados del Clasificador Random Forest Closed World\n")
        f.write("=====================================================\n\n")
        f.write(f"Shape del conjunto de entrenamiento: {resultados['train_shape']}\n")
        f.write(f"Shape del conjunto de test: {resultados['test_shape']}\n")
        f.write(f"Intersección entre train y test: {resultados['interseccion_train_test']}\n")
        f.write("\nNúmero de muestras por clase:\n")
        f.write(str(resultados["cont_clases"]))
        f.write(f"\nAccuracy: {resultados['accuracy']:.4f}\n")
        f.write(f"Aciertos: {resultados['aciertos']} de {resultados['total_test']}\n")
        f.write("\nMatriz de confusión:\n")
        cm = resultados["matriz_confusion"]
        for row in cm:
            f.write("  " + " ".join(f"{num:5d}" for num in row) + "\n")
        f.write("\nTop 20 features más importantes:\n")
        for feature, importance in resultados["top20_features"].items():
            f.write(f"  {feature}: {importance:.4f}\n")
        f.write(f"\nAccuracy con labels barajadas: {resultados['accuracy_shuffle']:.4f}\n")
        f.write(f"Aciertos con labels barajadas: {resultados['aciertos_shuffle']} de {resultados['total_test']}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clasificador Random Forest Closed World")

    parser.add_argument("csv", help="Ruta al CSV de features")
    parser.add_argument(
        "--output", "-o",
        default="resultados_clasificador.txt",
        help="Ruta del archivo de salida (.txt)"
    )

    args = parser.parse_args()

    resultados = clasificadorCW(args.csv)
    if args.output:
        guardar_resultados(resultados, args.output)