import sys
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker


# ─── Utilidades ──────────────────────────────────────────────────────────────

def remove_outliers_iqr(values, factor=1.5):
    if len(values) == 0:
        return values
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    lo, hi = q1 - factor * iqr, q3 + factor * iqr
    clean = values[(values >= lo) & (values <= hi)]
    return clean if len(clean) > 0 else values


def compute_stats(df, feat_x, feat_y, pages):
    stats = {}
    for page in pages:
        sub = df[df['label'] == page]
        vx = sub[feat_x].dropna().values.astype(float)
        vy = sub[feat_y].dropna().values.astype(float)
        if len(vx) == 0 or len(vy) == 0:
            stats[page] = None
            continue
        cx = remove_outliers_iqr(vx)
        cy = remove_outliers_iqr(vy)
        stats[page] = {
            'cx': cx, 'cy': cy,
            'xmin': cx.min(), 'xmax': cx.max(),
            'ymin': cy.min(), 'ymax': cy.max(),
        }
    return stats


def rects_overlap(a, b):
    """True si los rectángulos a y b se intersectan (inclusive en bordes)."""
    return (a['xmin'] <= b['xmax'] and a['xmax'] >= b['xmin'] and
            a['ymin'] <= b['ymax'] and a['ymax'] >= b['ymin'])


def compute_overlap_flags(pages, stats):
    flags = {}
    for page in pages:
        if stats[page] is None:
            flags[page] = False
            continue
        overlaps = any(
            other != page
            and stats[other] is not None
            and rects_overlap(stats[page], stats[other])
            for other in pages
        )
        flags[page] = overlaps
    return flags


# ─── Dibujo de un subplot (grupo de hasta 20 páginas) ────────────────────────

def plot_group_2d(ax, pages, stats, overlap_flags, feat_x, feat_y, colormap):
    """
    Pinta los rectángulos de cada página.
    Devuelve el nº de páginas con solapamiento en este grupo.
    """
    n = len(pages)
    colors = [colormap(i / max(n - 1, 1)) for i in range(n)]

    # Colectar todos los rangos para autoscale manual
    all_x, all_y = [], []

    rects_drawn = []  # (patch, page, xpos, ypos, color) para etiquetas

    for i, page in enumerate(pages):
        s = stats[page]
        if s is None:
            continue
        color = colors[i]
        flag  = overlap_flags[page]

        xmin, xmax = s['xmin'], s['xmax']
        ymin, ymax = s['ymin'], s['ymax']
        all_x += [xmin, xmax]
        all_y += [ymin, ymax]

        w = xmax - xmin
        h = ymax - ymin

        # ── Rectángulo de rango limpio ────────────────────────────────────
        # Fondo semitransparente del color de la página
        rect_bg = mpatches.FancyBboxPatch(
            (xmin, ymin), w, h,
            boxstyle="square,pad=0",
            linewidth=0,
            facecolor=(*matplotlib.colors.to_rgb(color), 0.12),
            zorder=2
        )
        ax.add_patch(rect_bg)

        # Borde: rojo grueso si hay solapamiento, color propio si limpio
        edge_color = '#c0392b' if flag else color
        edge_lw    = 1.6       if flag else 1.2
        edge_ls    = '-'       if flag else '-'
        rect_edge = mpatches.FancyBboxPatch(
            (xmin, ymin), w, h,
            boxstyle="square,pad=0",
            linewidth=edge_lw,
            linestyle=edge_ls,
            edgecolor=edge_color,
            facecolor='none',
            zorder=3
        )
        ax.add_patch(rect_edge)

        # Puntos dispersos dentro del rectángulo
        # Usamos los valores limpios de cada dimensión (muestreamos pares al azar)
        n_pts = min(len(s['cx']), len(s['cy']))
        idx_x = np.random.choice(len(s['cx']), n_pts, replace=False)
        idx_y = np.random.choice(len(s['cy']), n_pts, replace=False)
        ax.scatter(s['cx'][idx_x], s['cy'][idx_y],
                   color=color, alpha=0.35, s=18, linewidths=0, zorder=4)

        # Número de página en el centro del rectángulo
        cx_mid = (xmin + xmax) / 2
        cy_mid = (ymin + ymax) / 2
        page_num = page.split('_')[1]
        ax.text(cx_mid, cy_mid, page_num,
                ha='center', va='center',
                fontsize=5.5, color=color,
                fontweight='bold', alpha=0.7, zorder=5)

        rects_drawn.append((page, xmin, xmax, ymin, ymax, color, flag))

    # ── Región de intersección sombreada (entre pares que solapan) ────────
    for i in range(len(rects_drawn)):
        for j in range(i + 1, len(rects_drawn)):
            pa = rects_drawn[i]
            pb = rects_drawn[j]
            if not (stats[pa[0]] and stats[pb[0]]):
                continue
            # Calcular intersección
            ix_min = max(pa[1], pb[1])
            ix_max = min(pa[2], pb[2])
            iy_min = max(pa[3], pb[3])
            iy_max = min(pa[4], pb[4])
            if ix_max > ix_min and iy_max > iy_min:
                inter = mpatches.FancyBboxPatch(
                    (ix_min, iy_min),
                    ix_max - ix_min, iy_max - iy_min,
                    boxstyle="square,pad=0",
                    linewidth=0.8,
                    linestyle='--',
                    edgecolor='#c0392b',
                    facecolor=(0.83, 0.22, 0.18, 0.18),
                    zorder=6
                )
                ax.add_patch(inter)

    # ── Autoscale con margen ──────────────────────────────────────────────
    if all_x and all_y:
        xr = max(all_x) - min(all_x) or 1
        yr = max(all_y) - min(all_y) or 1
        margin_x = xr * 0.08
        margin_y = yr * 0.08
        ax.set_xlim(min(all_x) - margin_x, max(all_x) + margin_x)
        ax.set_ylim(min(all_y) - margin_y, max(all_y) + margin_y)

    # ── Estética ──────────────────────────────────────────────────────────
    ax.set_xlabel(feat_x, fontsize=12, color='#111111', labelpad=5)
    ax.set_ylabel(feat_y, fontsize=12, color='#111111', labelpad=5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#111111')
    ax.spines['bottom'].set_color('#111111')
    ax.tick_params(colors='#111111', labelsize=11)
    ax.set_facecolor('white')
    ax.grid(color='#aaaaaa', linewidth=0.8, linestyle=':', zorder=0)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda v, _: f'{v/1e3:.0f}k' if abs(v) >= 1000 else f'{v:.3g}'))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda v, _: f'{v/1e3:.0f}k' if abs(v) >= 1000 else f'{v:.3g}'))

    # ── Indicadores 0/1 ──────────────────────────────────────────────────
    # Se pintan como pequeños cuadros de texto en el margen superior derecho
    # del subplot, uno por página, ordenados por número
    group_sum = sum(int(overlap_flags[p]) for p in pages if overlap_flags[p] is not None)

    return group_sum


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('feat_x')
    parser.add_argument('feat_y')
    parser.add_argument('output_dir')
    parser.add_argument('--n_pages', type=int, default=None,
                        help='Número máximo de páginas a graficar (por defecto todas)')
    args = parser.parse_args()

    csv_path   = args.csv_path
    feat_x     = args.feat_x
    feat_y     = args.feat_y
    output_dir = args.output_dir

    if not os.path.isfile(csv_path):
        print(f"[ERROR] CSV no encontrado: {csv_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Cargando CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    for feat in (feat_x, feat_y):
        if feat not in df.columns:
            print(f"[ERROR] Feature '{feat}' no existe en el CSV.")
            sys.exit(1)

    all_pages = [f'pagina_{i}' for i in range(1, 101)]
    existing  = set(df['label'].unique())
    pages     = [p for p in all_pages if p in existing]

    if not pages:
        print("[ERROR] No se encontraron etiquetas pagina_1..pagina_100.")
        sys.exit(1)

    if args.n_pages is not None:
        pages = pages[:args.n_pages]
        print(f"Limitando a {args.n_pages} páginas (--n_pages)")

    print(f"Páginas a graficar: {len(pages)}  |  X={feat_x}  |  Y={feat_y}")
    print("Calculando rangos limpios (IQR)...")
    stats = compute_stats(df, feat_x, feat_y, pages)

    print("Calculando solapamientos 2D...")
    overlap_flags = compute_overlap_flags(pages, stats)
    total_overlap = sum(int(v) for v in overlap_flags.values())
    total_pages   = len(pages)
    pct           = 100 * total_overlap / total_pages
    print(f"  → Páginas con solapamiento 2D: {total_overlap} / {total_pages}  ({pct:.1f} %)")

    groups   = [pages[i:i+25] for i in range(0, len(pages), 25)]
    n_groups = len(groups)
    n_cols   = 2
    n_rows   = (n_groups + 1) // 2

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(14, 6.5 * n_rows),
        facecolor='white'
    )
    axes = np.array(axes).flatten()
    for ax in axes[n_groups:]:
        ax.set_visible(False)

    colormap   = plt.get_cmap('tab10')
    group_sums = []

    for idx, (ax, group) in enumerate(zip(axes, groups)):
        g_sum = plot_group_2d(ax, group, stats, overlap_flags,
                              feat_x, feat_y, colormap)
        group_sums.append(g_sum)

        first_p = int(group[0].split('_')[1])
        last_p  = int(group[-1].split('_')[1])

        # Indicadores 0/1 encima del subplot como texto compacto
        flag_str = ''.join(
            f'[{"1" if overlap_flags[p] else "0"}]' for p in group
        )
        ax.set_title(
            f'Págs {first_p}–{last_p}   Σ={g_sum}/{len(group)}\n'
            f'{"".join(["1" if overlap_flags[p] else "0" for p in group])}',
            fontsize=12, color='#111111', pad=6, loc='center',
            fontfamily='monospace'
        )

    # ── Suptitle global ───────────────────────────────────────────────────
    fig.suptitle(
        f'Σ total solapamiento 2D  =  {total_overlap} / {total_pages}  ({pct:.1f} %)'
        f'     [{feat_x}  ×  {feat_y}]',
        fontsize=14, fontweight='bold', color='#1a1a2e',
        fontfamily='monospace', y=1.03
    )

    plt.tight_layout(h_pad=3.0, w_pad=2.0)

    suffix = f'_top{len(pages)}' if args.n_pages is not None else ''
    out = os.path.join(output_dir, f'scatter2d_{feat_x}__{feat_y}{suffix}.png')
    plt.savefig(out, dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    # ── Resumen consola ───────────────────────────────────────────────────
    print("\n─── Resumen por grupo ─────────────────────────────────────────")
    for group, g_sum in zip(groups, group_sums):
        first = int(group[0].split('_')[1])
        last  = int(group[-1].split('_')[1])
        bits  = ''.join('1' if overlap_flags[p] else '0' for p in group)
        print(f"  Págs {first:>3}–{last:<3}  [{bits}]  Σ={g_sum}/{len(group)}")
    print(f"\n  TOTAL  →  {total_overlap} / {total_pages}  ({pct:.1f} %)")
    print(f"\n✓ Guardado en: {out}")


if __name__ == '__main__':
    np.random.seed(42)
    main()
