import sys
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def remove_outliers_iqr(values, factor=1.5):
    if len(values) == 0:
        return values, None, None
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    mask = (values >= lower) & (values <= upper)
    return values[mask], lower, upper


def compute_page_stats(df, feature, pages):
    stats = {}
    for page in pages:
        subset = df[df['label'] == page][feature].dropna().values.astype(float)
        if len(subset) == 0:
            stats[page] = {'values': np.array([]), 'min': None, 'max': None}
            continue
        clean, _, _ = remove_outliers_iqr(subset)
        if len(clean) == 0:
            clean = subset
        stats[page] = {
            'values': clean,
            'min': float(clean.min()),
            'max': float(clean.max()),
        }
    return stats


def compute_overlap_flags(pages, stats):
    """
    Para cada página P: True si algún valor de P cae en el rango [min,max]
    de CUALQUIER otra página Q (comparación global, no solo adyacentes).
    """
    overlap_flags = {}
    for page in pages:
        vals = stats[page]['values']
        if len(vals) == 0:
            overlap_flags[page] = False
            continue
        overlaps = False
        for other in pages:
            if other == page:
                continue
            o_min = stats[other]['min']
            o_max = stats[other]['max']
            if o_min is None or o_max is None:
                continue
            if np.any((vals >= o_min) & (vals <= o_max)):
                overlaps = True
                break
        overlap_flags[page] = overlaps
    return overlap_flags


def plot_group(ax, pages, stats, overlap_flags, colormap):
    n = len(pages)
    x_positions = np.arange(1, n + 1)
    colors = [colormap(i / max(n - 1, 1)) for i in range(n)]

    for i, (page, xpos) in enumerate(zip(pages, x_positions)):
        vals = stats[page]['values']
        if len(vals) == 0:
            continue
        color = colors[i]
        vmin = stats[page]['min']
        vmax = stats[page]['max']

        # Puntos con jitter
        jitter = np.random.uniform(-0.18, 0.18, size=len(vals))
        ax.scatter(xpos + jitter, vals,
                   color=color, alpha=0.45, s=18, linewidths=0, zorder=2)

        # Barras min/max y línea vertical de rango
        ax.hlines(vmin, xpos - 0.3, xpos + 0.3,
                  colors=color, linewidths=2.5, alpha=0.9, zorder=3)
        ax.hlines(vmax, xpos - 0.3, xpos + 0.3,
                  colors=color, linewidths=2.5, alpha=0.9, zorder=3)
        ax.vlines(xpos, vmin, vmax,
                  colors=color, linewidths=0.6, alpha=0.4, zorder=1)

    # Límites entre páginas adyacentes
    for i in range(n - 1):
        page_a, page_b = pages[i], pages[i + 1]
        if stats[page_a]['max'] is None or stats[page_b]['min'] is None:
            continue
        max_a = stats[page_a]['max']
        min_b = stats[page_b]['min']
        x_mid = (x_positions[i] + x_positions[i + 1]) / 2.0

        ax.axvline(x=x_mid, color='#e74c3c', linewidth=0.8,
                   linestyle='--', alpha=0.55, zorder=4)
        if max_a < min_b:
            midpoint = (max_a + min_b) / 2.0
            ax.hlines(midpoint, x_mid - 0.35, x_mid + 0.35,
                      colors='#e74c3c', linewidths=1.2,
                      linestyles='-', alpha=0.85, zorder=5)

    # ── Etiquetas 0/1 encima de cada página ──────────────────────────────
    ax.autoscale(axis='y')
    cur_ymin, cur_ymax = ax.get_ylim()
    y_range = cur_ymax - cur_ymin
    label_y  = cur_ymax + y_range * 0.01
    new_ymax = cur_ymax + y_range * 0.18
    ax.set_ylim(cur_ymin, new_ymax)

    group_sum = 0
    for i, (page, xpos) in enumerate(zip(pages, x_positions)):
        flag = overlap_flags.get(page, False)
        group_sum += int(flag)
        txt   = '1' if flag else '0'
        color_txt = '#c0392b' if flag else '#27ae60'
        ax.text(xpos, label_y, txt,
                ha='center', va='bottom',
                fontsize=8.5, fontweight='bold',
                color=color_txt, zorder=6)

    # Etiquetas eje x
    page_numbers = [int(p.split('_')[1]) for p in pages]
    ax.set_xticks(x_positions)
    ax.set_xticklabels(page_numbers, fontsize=11, color='#111111')
    ax.set_xlim(0.3, n + 0.7)

    # Estética
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#111111')
    ax.spines['bottom'].set_color('#111111')
    ax.tick_params(colors='#111111', labelsize=11)
    ax.set_facecolor('white')
    ax.grid(axis='y', color='#aaaaaa', linewidth=0.8, linestyle=':', zorder=0)

    return group_sum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('feature')
    parser.add_argument('output_dir')
    parser.add_argument('--n_pages', type=int, default=None,
                        help='Número máximo de páginas a graficar (por defecto todas)')
    args = parser.parse_args()

    csv_path   = args.csv_path
    feature    = args.feature
    output_dir = args.output_dir

    if not os.path.isfile(csv_path):
        print(f"[ERROR] No se encuentra el CSV: {csv_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Cargando CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    if 'label' not in df.columns:
        print("[ERROR] El CSV no tiene columna 'label'.")
        sys.exit(1)
    if feature not in df.columns:
        print(f"[ERROR] La feature '{feature}' no existe en el CSV.")
        sys.exit(1)

    all_pages = [f'pagina_{i}' for i in range(1, 101)]
    existing  = set(df['label'].unique())
    pages     = [p for p in all_pages if p in existing]

    if len(pages) == 0:
        print("[ERROR] No se encontraron etiquetas pagina_1..pagina_100 en el CSV.")
        sys.exit(1)

    if args.n_pages is not None:
        pages = pages[:args.n_pages]
        print(f"Limitando a {args.n_pages} páginas (--n_pages)")

    print(f"Páginas a graficar: {len(pages)}")
    print(f"Feature: {feature}")
    print("Calculando estadísticos y eliminando outliers...")
    stats = compute_page_stats(df, feature, pages)

    print("Calculando flags de solapamiento (comparación global)...")
    overlap_flags = compute_overlap_flags(pages, stats)

    total_overlap = sum(int(v) for v in overlap_flags.values())
    total_pages   = len(pages)
    print(f"  → Páginas con solapamiento: {total_overlap} / {total_pages}")

    groups   = [pages[i:i+20] for i in range(0, len(pages), 20)]
    n_groups = len(groups)

    fig, axes = plt.subplots(n_groups, 1,
                             figsize=(22, 5.4 * n_groups),
                             facecolor='white')
    if n_groups == 1:
        axes = [axes]

    colormap   = plt.get_cmap('tab10')
    group_sums = []

    for idx, (ax, group) in enumerate(zip(axes, groups)):
        g_sum = plot_group(ax, group, stats, overlap_flags, colormap)
        group_sums.append(g_sum)

        ax.set_ylabel(feature, fontsize=12, color='#111111', labelpad=6)
        ax.set_xlabel('página', fontsize=12, color='#111111', labelpad=4)

        first_p = int(group[0].split('_')[1])
        last_p  = int(group[-1].split('_')[1])
        ax.set_title(
            f'Páginas {first_p}–{last_p}   │   '
            f'Σ solapamiento = {g_sum} / {len(group)}',
            fontsize=12, color='#111111', pad=5, loc='left',
            fontfamily='monospace'
        )

    # ── Sumatorio global como suptitle ────────────────────────────────────
    pct = 100 * total_overlap / total_pages
    fig.suptitle(
        f'Σ total solapamiento = {total_overlap} / {total_pages}  ({pct:.1f} %)',
        fontsize=14, fontweight='bold', color='#1a1a2e',
        fontfamily='monospace', y=1.004
    )

    plt.tight_layout(h_pad=3.5)

    suffix = f'_top{len(pages)}' if args.n_pages is not None else ''
    output_path = os.path.join(output_dir, f'scatter_{feature}{suffix}.png')
    plt.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    # ── Resumen en consola ────────────────────────────────────────────────
    print("\n─── Resumen por grupo ───────────────────────────────────────")
    for group, g_sum in zip(groups, group_sums):
        first = int(group[0].split('_')[1])
        last  = int(group[-1].split('_')[1])
        flags_str = ''.join('1' if overlap_flags[p] else '0' for p in group)
        print(f"  Páginas {first:>3}–{last:<3}  [{flags_str}]  Σ={g_sum}/{len(group)}")
    print(f"\n  TOTAL  →  {total_overlap} / {total_pages}  ({pct:.1f} %)")
    print(f"\n✓ Gráfica guardada en: {output_path}")


if __name__ == '__main__':
    np.random.seed(42)
    main()

