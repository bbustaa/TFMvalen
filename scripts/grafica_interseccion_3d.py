import sys
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.ticker as ticker


# ─── Outliers ────────────────────────────────────────────────────────────────

def clean_iqr(values, factor=1.5):
    if len(values) == 0:
        return values
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    c = values[(values >= q1 - factor*iqr) & (values <= q3 + factor*iqr)]
    return c if len(c) > 0 else values


# ─── Stats ────────────────────────────────────────────────────────────────────

def compute_stats(df, fx, fy, fz, pages):
    stats = {}
    for page in pages:
        sub = df[df['label'] == page]
        vx = clean_iqr(sub[fx].dropna().values.astype(float))
        vy = clean_iqr(sub[fy].dropna().values.astype(float))
        vz = clean_iqr(sub[fz].dropna().values.astype(float))
        if len(vx) == 0 or len(vy) == 0 or len(vz) == 0:
            stats[page] = None
            continue
        stats[page] = dict(
            xmin=vx.min(), xmax=vx.max(),
            ymin=vy.min(), ymax=vy.max(),
            zmin=vz.min(), zmax=vz.max(),
            cx=vx, cy=vy, cz=vz,
        )
    return stats


# ─── Overlap 3D ───────────────────────────────────────────────────────────────

def cubes_overlap(a, b):
    return (a['xmin'] <= b['xmax'] and a['xmax'] >= b['xmin'] and
            a['ymin'] <= b['ymax'] and a['ymax'] >= b['ymin'] and
            a['zmin'] <= b['zmax'] and a['zmax'] >= b['zmin'])


def compute_overlap_flags(pages, stats):
    flags = {}
    for page in pages:
        if stats[page] is None:
            flags[page] = False
            continue
        flags[page] = any(
            o != page and stats[o] is not None and cubes_overlap(stats[page], stats[o])
            for o in pages
        )
    return flags


# ─── Dibujo de un cubo (wireframe + caras semitransparentes) ─────────────────

def cube_faces(xmin, xmax, ymin, ymax, zmin, zmax):
    """Devuelve lista de 6 caras (cada cara = lista de 4 vértices)."""
    v = np.array([
        [xmin, ymin, zmin], [xmax, ymin, zmin],
        [xmax, ymax, zmin], [xmin, ymax, zmin],
        [xmin, ymin, zmax], [xmax, ymin, zmax],
        [xmax, ymax, zmax], [xmin, ymax, zmax],
    ])
    faces = [
        [v[0], v[1], v[2], v[3]],  # bottom
        [v[4], v[5], v[6], v[7]],  # top
        [v[0], v[1], v[5], v[4]],  # front
        [v[2], v[3], v[7], v[6]],  # back
        [v[0], v[3], v[7], v[4]],  # left
        [v[1], v[2], v[6], v[5]],  # right
    ]
    return faces


def draw_cube(ax, s, color, flag, alpha_face=0.06, alpha_edge=0.75):
    faces = cube_faces(s['xmin'], s['xmax'],
                       s['ymin'], s['ymax'],
                       s['zmin'], s['zmax'])
    edge_color = '#c0392b' if flag else color
    edge_lw    = 1.4       if flag else 0.9

    poly = Poly3DCollection(faces,
                            facecolor=(*matplotlib.colors.to_rgb(color), alpha_face),
                            edgecolor=edge_color,
                            linewidth=edge_lw,
                            zsort='min')
    ax.add_collection3d(poly)


def draw_intersection_cube(ax, a, b):
    """Dibuja el cubo de intersección entre a y b si existe."""
    ix0 = max(a['xmin'], b['xmin']); ix1 = min(a['xmax'], b['xmax'])
    iy0 = max(a['ymin'], b['ymin']); iy1 = min(a['ymax'], b['ymax'])
    iz0 = max(a['zmin'], b['zmin']); iz1 = min(a['zmax'], b['zmax'])
    if ix1 > ix0 and iy1 > iy0 and iz1 > iz0:
        faces = cube_faces(ix0, ix1, iy0, iy1, iz0, iz1)
        poly = Poly3DCollection(faces,
                                facecolor=(0.83, 0.15, 0.15, 0.30),
                                edgecolor='#c0392b',
                                linewidth=0.8,
                                linestyle='--',
                                zsort='min')
        ax.add_collection3d(poly)


# ─── Subplot ──────────────────────────────────────────────────────────────────

def plot_group_3d(ax, pages, stats, overlap_flags, fx, fy, fz, colormap):
    n = len(pages)
    colors = [colormap(i / max(n-1, 1)) for i in range(n)]

    all_x, all_y, all_z = [], [], []

    valid = [(page, colors[i]) for i, page in enumerate(pages) if stats[page]]

    # ── Cubos principales ─────────────────────────────────────────────────
    for page, color in valid:
        s    = stats[page]
        flag = overlap_flags[page]
        draw_cube(ax, s, color, flag)

        n_pts = min(len(s['cx']), len(s['cy']), len(s['cz']), 60)
        ix = np.random.choice(len(s['cx']), n_pts, replace=False)
        iy = np.random.choice(len(s['cy']), n_pts, replace=False)
        iz = np.random.choice(len(s['cz']), n_pts, replace=False)
        ax.scatter(s['cx'][ix], s['cy'][iy], s['cz'][iz],
                   color=color, alpha=0.30, s=18, linewidths=0, zorder=2,
                   depthshade=True)

        # Número de página en el centro del cubo
        cx = (s['xmin']+s['xmax'])/2
        cy = (s['ymin']+s['ymax'])/2
        cz = (s['zmin']+s['zmax'])/2
        ax.text(cx, cy, cz, page.split('_')[1],
                fontsize=5, color=color, fontweight='bold',
                ha='center', va='center', alpha=0.75, zorder=5)

        all_x += [s['xmin'], s['xmax']]
        all_y += [s['ymin'], s['ymax']]
        all_z += [s['zmin'], s['zmax']]

    # ── Intersecciones ────────────────────────────────────────────────────
    for i in range(len(valid)):
        for j in range(i+1, len(valid)):
            pa, pb = valid[i][0], valid[j][0]
            if cubes_overlap(stats[pa], stats[pb]):
                draw_intersection_cube(ax, stats[pa], stats[pb])

    # ── Límites de ejes ───────────────────────────────────────────────────
    def axis_lim(vals):
        lo, hi = min(vals), max(vals)
        m = (hi - lo) * 0.07 or 1
        return lo - m, hi + m

    if all_x:
        ax.set_xlim(*axis_lim(all_x))
        ax.set_ylim(*axis_lim(all_y))
        ax.set_zlim(*axis_lim(all_z))

    # ── Estética ──────────────────────────────────────────────────────────
    fmt = ticker.FuncFormatter(
        lambda v, _: f'{v/1e3:.0f}k' if abs(v) >= 1000 else f'{v:.3g}')
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)
    ax.zaxis.set_major_formatter(fmt)
    ax.set_xlabel(fx, fontsize=12, labelpad=4, color='#111111')
    ax.set_ylabel(fy, fontsize=12, labelpad=4, color='#111111')
    ax.set_zlabel(fz, fontsize=12, labelpad=4, color='#111111')
    ax.tick_params(labelsize=11, colors='#111111')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('#aaaaaa')
    ax.yaxis.pane.set_edgecolor('#aaaaaa')
    ax.zaxis.pane.set_edgecolor('#aaaaaa')
    ax.grid(True, color='#aaaaaa', linewidth=0.8, linestyle=':')
    ax.set_facecolor('white')
    ax.view_init(elev=22, azim=35)

    g_sum = sum(int(overlap_flags[p]) for p in pages if overlap_flags[p] is not None)
    return g_sum


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('fx')
    parser.add_argument('fy')
    parser.add_argument('fz')
    parser.add_argument('output_dir')
    parser.add_argument('--n_pages', type=int, default=None,
                        help='Número máximo de páginas a graficar (por defecto todas)')
    args = parser.parse_args()

    csv_path, fx, fy, fz, output_dir = (
        args.csv_path, args.fx, args.fy, args.fz, args.output_dir)

    if not os.path.isfile(csv_path):
        print(f"[ERROR] CSV no encontrado: {csv_path}"); sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Cargando CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    for feat in (fx, fy, fz):
        if feat not in df.columns:
            print(f"[ERROR] Feature '{feat}' no existe."); sys.exit(1)

    all_pages = [f'pagina_{i}' for i in range(1, 101)]
    pages     = [p for p in all_pages if p in set(df['label'].unique())]

    if not pages:
        print("[ERROR] No se encontraron etiquetas pagina_1..pagina_100."); sys.exit(1)

    if args.n_pages is not None:
        pages = pages[:args.n_pages]
        print(f"Limitando a {args.n_pages} páginas (--n_pages)")

    print(f"Páginas a graficar: {len(pages)}  |  X={fx}  Y={fy}  Z={fz}")
    print("Calculando rangos limpios (IQR)...")
    stats = compute_stats(df, fx, fy, fz, pages)

    print("Calculando solapamientos 3D...")
    overlap_flags = compute_overlap_flags(pages, stats)
    total_overlap = sum(int(v) for v in overlap_flags.values())
    total_pages   = len(pages)
    pct           = 100 * total_overlap / total_pages
    print(f"  → Páginas con solapamiento 3D: {total_overlap} / {total_pages}  ({pct:.1f} %)")

    groups   = [pages[i:i+20] for i in range(0, len(pages), 20)]
    n_groups = len(groups)

    fig = plt.figure(figsize=(8, 7.5 * n_groups), facecolor='white')

    colormap   = plt.get_cmap('tab10')
    group_sums = []

    for idx, group in enumerate(groups):
        ax = fig.add_subplot(n_groups, 1, idx+1, projection='3d')
        g_sum = plot_group_3d(ax, group, stats, overlap_flags,
                              fx, fy, fz, colormap)
        group_sums.append(g_sum)

        first_p = int(group[0].split('_')[1])
        last_p  = int(group[-1].split('_')[1])
        bits    = ''.join('1' if overlap_flags[p] else '0' for p in group)
        ax.set_title(
            f'Págs {first_p}–{last_p}   Σ={g_sum}/{len(group)}\n{bits}',
            fontsize=12, color='#111111', pad=6,
            fontfamily='monospace'
        )

    fig.suptitle(
        f'Σ total solapamiento 3D  =  {total_overlap} / {total_pages}  ({pct:.1f} %)'
        f'     [{fx}  ×  {fy}  ×  {fz}]',
        fontsize=14, fontweight='bold', color='#1a1a2e',
        fontfamily='monospace', y=1.03
    )

    plt.tight_layout(h_pad=2.5)

    suffix = f'_top{len(pages)}' if args.n_pages is not None else ''
    out = os.path.join(output_dir, f'scatter3d_{fx}__{fy}__{fz}{suffix}.png')
    plt.savefig(out, dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

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

