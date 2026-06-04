import sys
import os
import numpy as np
import pandas as pd


def remove_outliers_iqr(values, factor=1.5):
    if len(values) == 0:
        return values

    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1

    lower = q1 - factor * iqr
    upper = q3 + factor * iqr

    clean = values[(values >= lower) & (values <= upper)]
    return clean if len(clean) > 0 else values


def compute_ranges_nd(df, features, pages):
    stats = {}

    for page in pages:
        sub = df[df["label"] == page]
        stats[page] = {}

        valid_page = True

        for feature in features:
            values = sub[feature].dropna().values.astype(float)

            if len(values) == 0:
                valid_page = False
                break

            clean = remove_outliers_iqr(values)

            stats[page][feature] = {
                "min": float(clean.min()),
                "max": float(clean.max()),
                "n_values": int(len(clean))
            }

        if not valid_page:
            stats[page] = None

    return stats


def hyperrectangles_overlap(stats_a, stats_b, features):
    
    for feature in features:
        min_a = stats_a[feature]["min"]
        max_a = stats_a[feature]["max"]

        min_b = stats_b[feature]["min"]
        max_b = stats_b[feature]["max"]

        # Si en una feature no se cruzan, NO hay solapamiento
        if max_a < min_b or max_b < min_a:
            return False

    return True


def compute_overlap_nd(df, features, pages):
    stats = compute_ranges_nd(df, features, pages)

    overlap_flags = {}
    overlap_pairs = []

    for page in pages:
        if stats[page] is None:
            overlap_flags[page] = False
            continue

        overlaps = False

        for other in pages:
            if other == page or stats[other] is None:
                continue

            if hyperrectangles_overlap(stats[page], stats[other], features):
                overlaps = True

                # Guardamos cada par una sola vez
                if page < other:
                    overlap_pairs.append((page, other))

        overlap_flags[page] = overlaps

    total_overlap_pages = sum(int(v) for v in overlap_flags.values())

    return stats, overlap_flags, overlap_pairs, total_overlap_pages


def main():
    if len(sys.argv) != 4:
        print("Uso:")
        print("  python scripts/solapamiento_nd.py <csv_path> <features_separadas_por_comas> <output_dir>")
        print()
        print("Ejemplo:")
        print("  python scripts/solapamiento_nd.py datos/features.csv feature_2,feature_18565,feature_18564 resultados/")
        sys.exit(1)

    csv_path = sys.argv[1]
    features_arg = sys.argv[2]
    output_dir = sys.argv[3]

    features = [f.strip() for f in features_arg.split(",") if f.strip()]

    if not os.path.isfile(csv_path):
        print(f"No se encuentra el CSV: {csv_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Cargando CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    if "label" not in df.columns:
        print("El CSV no tiene columna 'label'.")
        sys.exit(1)

    for feature in features:
        if feature not in df.columns:
            print(f"La feature '{feature}' no existe en el CSV.")
            sys.exit(1)

    #all_pages = [f"pagina_{i}" for i in range(1, 101)]
    #existing = set(df["label"].unique())
    #pages = [p for p in all_pages if p in existing]
    
    pages = sorted(df["label"].unique().tolist())

    if len(pages) == 0:
        print("No se encontró etiqueta.")
        sys.exit(1)

    print(f"Páginas encontradas: {len(pages)}")
    print(f"Features usadas ({len(features)}): {features}")
    print("Calculando solapamiento N-dimensional...")

    stats, overlap_flags, overlap_pairs, total_overlap_pages = compute_overlap_nd(
        df, features, pages
    )

    total_pages = len(pages)
    pct_overlap = 100 * total_overlap_pages / total_pages

    print()
    print("─── Resultado global ─────────────────────────────")
    print(f"Nº de features: {len(features)}")
    print(f"Páginas con solapamiento: {total_overlap_pages} / {total_pages}")
    print(f"Porcentaje de solapamiento: {pct_overlap:.2f} %")
    print(f"Nº de pares solapados: {len(overlap_pairs)}")

    # -----------------------------
    # Guardar resumen global
    # -----------------------------
    resumen_path = os.path.join(output_dir, f"solapamiento_nd_{len(features)}features_resumen.txt")

    with open(resumen_path, "w", encoding="utf-8") as f:
        f.write("Resumen de solapamiento N-dimensional\n")
        f.write("=====================================\n\n")
        f.write(f"CSV: {csv_path}\n")
        f.write(f"Nº de features: {len(features)}\n")
        f.write(f"Features usadas: {', '.join(features)}\n\n")
        f.write(f"Páginas analizadas: {total_pages}\n")
        f.write(f"Páginas con solapamiento: {total_overlap_pages} / {total_pages}\n")
        f.write(f"Porcentaje de solapamiento: {pct_overlap:.2f} %\n")
        f.write(f"Nº de pares solapados: {len(overlap_pairs)}\n\n")

        f.write("Flags por página:\n")
        for page in pages:
            flag = 1 if overlap_flags[page] else 0
            f.write(f"{page}: {flag}\n")

    # -----------------------------
    # Guardar pares solapados
    # -----------------------------
    pairs_path = os.path.join(output_dir, f"solapamiento_nd_{len(features)}features_pares.csv")

    pairs_df = pd.DataFrame(overlap_pairs, columns=["pagina_a", "pagina_b"])
    pairs_df.to_csv(pairs_path, index=False)

    # -----------------------------
    # Guardar flags por página
    # -----------------------------
    flags_path = os.path.join(output_dir, f"solapamiento_nd_{len(features)}features_flags.csv")

    flags_df = pd.DataFrame({
        "pagina": pages,
        "solapamiento": [int(overlap_flags[p]) for p in pages]
    })

    flags_df.to_csv(flags_path, index=False)

    # -----------------------------
    # Guardar rangos min/max
    # -----------------------------
    ranges_rows = []

    for page in pages:
        if stats[page] is None:
            continue

        row = {"pagina": page}

        for feature in features:
            row[f"{feature}_min"] = stats[page][feature]["min"]
            row[f"{feature}_max"] = stats[page][feature]["max"]

        ranges_rows.append(row)

    ranges_df = pd.DataFrame(ranges_rows)
    ranges_path = os.path.join(output_dir, f"solapamiento_nd_{len(features)}features_rangos.csv")
    ranges_df.to_csv(ranges_path, index=False)

    print()
    print("─── Archivos guardados ───────────────────────────")
    print(f"Resumen: {resumen_path}")
    print(f"Pares solapados: {pairs_path}")
    print(f"Flags por página: {flags_path}")
    print(f"Rangos min/max: {ranges_path}")


if __name__ == "__main__":
    main()
