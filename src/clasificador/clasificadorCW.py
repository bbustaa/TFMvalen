import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# bueno lo primero cargar el csv con los features :)
# cada fila contiene una muestra correspondiente a una captura
df = pd.read_csv("datos/prueba1/escenario1/features/features.csv")

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

    train_idx.extend(indices[:16])   # 16 para train
    test_idx.extend(indices[16:])    # el resto para test

# se construyen los dataframes de train y test usando los índices seleccionados
df_train = df.loc[train_idx]
df_test = df.loc[test_idx]

# se muestra el número de muestras en cada conjunto --> mas que todo para comprobar
# que se está haciendo bien :)
print("Train:", df_train.shape)
print("Test:", df_test.shape)

# comprobación de que no hay solapamiento entre train y test
train_set = set(train_idx)
test_set = set(test_idx)

print("Intersección train/test:", len(train_set.intersection(test_set)))    # intersecciòn debe ser 0 --> en caso contrario --> fuga de info
print("\nNúmero de muestras por clase:")                                    # nùmero de muestras por por clase en el dataset --> todas las pàginas deben tener el mismo nùmero                           
print(df["label"].value_counts().sort_index())

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
print("\nResultado OG")
print("Accuracy:", acc)
print("Aciertos:", (y_pred == y_test).sum(), "de", len(y_test))

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

print("\nPrueba barajeada (?)")
print("Accuracy con labels barajadas:", acc_shuffle)
print("Aciertos con labels barajadas:", (y_pred_shuffle == y_test).sum(), "de", len(y_test))
