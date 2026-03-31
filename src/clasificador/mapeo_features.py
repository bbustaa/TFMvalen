
def construir_mapa_features() -> dict:
    mapa = {}

    # (a) Connection stats
    mapa["feature_0"] = "incoming_tls_records"
    mapa["feature_1"] = "outgoing_tls_records"
    mapa["feature_2"] = "total_tls_bytes"

    # (b) Burst method 1
    nombres_b1 = ["min", "max", "std", "mean", "median"]
    for i, nombre in enumerate(nombres_b1, start=3):
        mapa[f"feature_{i}"] = f"burst_method1_{nombre}"

    # (b) Burst method 2
    nombres_b2 = ["min", "max", "std", "mean", "median"]
    for i, nombre in enumerate(nombres_b2, start=8):
        mapa[f"feature_{i}"] = f"burst_method2_blocks20_{nombre}"

    # (c) Distinct sizes
    mapa["feature_13"] = "distinct_incoming_sizes"
    mapa["feature_14"] = "distinct_outgoing_sizes"

    # (d) 20 least frequent incoming sizes
    for idx in range(15, 35):
        pos = idx - 14
        mapa[f"feature_{idx}"] = f"top20_leastfreq_incoming_size_{pos}"

    # (d) 20 least frequent outgoing sizes
    for idx in range(35, 55):
        pos = idx - 34
        mapa[f"feature_{idx}"] = f"top20_leastfreq_outgoing_size_{pos}"

    # (e) Frequency per incoming size [1..18432]
    for size in range(1, 18433):
        feature_idx = 54 + size
        mapa[f"feature_{feature_idx}"] = f"incoming_size_freq_{size}"

    # (e) Frequency per outgoing size [1..18432]
    for size in range(1, 18433):
        feature_idx = 18486 + size
        mapa[f"feature_{feature_idx}"] = f"outgoing_size_freq_{size}"

    return mapa

MAPA_FEATURES = construir_mapa_features()

def nombre_feature(feature_name: str) -> str:
    return MAPA_FEATURES.get(feature_name, feature_name)