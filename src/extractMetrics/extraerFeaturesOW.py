import csv
import os
import sys
import statistics
import argparse
from datetime import datetime
from mapeo_pcaps_OW import cargar_mapeo_pcaps, cargar_dominios_monitorizados

# Añadimos featuresH2C al path para poder importar los módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'featuresH2C'))

import a_ConnStats
import b1_BurstStats
import b2_BurstStats
import c_NumDiffSizes
import d_Top20Sizes
import e_SizeDist

def extraer_todas_las_features_OW(
    frames: list,
    client_ip: str,
    server_ip: str,
    server_port: int,
) -> list:
    # Ensambla el vector de 36 919 features llamando a cada módulo de featuresH2C.

    # A: ConnStats → [0 … 2]
    total_incoming, total_outgoing, total_bytes = a_ConnStats.calcular_conn_stats(
        frames, client_ip
    )

    # B1: burst bytes del servidor entre paquetes del cliente → [3 … 7]
    burst_b1 = b1_BurstStats.calcular_bursts_b1(frames, client_ip, server_ip, server_port)
    min_b1, max_b1, std_b1, mean_b1, median_b1 = _burst_stats(burst_b1)

    # B2: records del servidor por bloques de 20 → [8 … 12]
    bloques_b2 = b2_BurstStats.calcular_bursts_b2(frames, client_ip, server_ip, server_port)
    min_b2, max_b2, std_b2, mean_b2, median_b2 = _burst_stats(bloques_b2)

    # C: número de tamaños TLS distintos → [13 … 14]
    incoming_sizes, outgoing_sizes = c_NumDiffSizes.obtener_tamanos_from_frames(
        frames, client_ip
    )
    num_incoming_diff = len(set(incoming_sizes))
    num_outgoing_diff = len(set(outgoing_sizes))

    # D: top-20 tamaños menos frecuentes → [15 … 54]
    incoming_top20 = d_Top20Sizes.obtener_20_tamanos_menos_frecuentes(incoming_sizes)
    outgoing_top20 = d_Top20Sizes.obtener_20_tamanos_menos_frecuentes(outgoing_sizes)

    # E: distribución de frecuencias de tamaños → [55 … 36 918]
    incoming_freq, outgoing_freq = e_SizeDist.calcular_distribucion_from_frames(
        frames, client_ip
    )

    vector = []
    vector += [total_incoming, total_outgoing, total_bytes]
    vector += [min_b1, max_b1, std_b1, mean_b1, median_b1]
    vector += [min_b2, max_b2, std_b2, mean_b2, median_b2]
    vector += [num_incoming_diff, num_outgoing_diff]
    vector += incoming_top20
    vector += outgoing_top20
    vector += incoming_freq
    vector += outgoing_freq

    assert len(vector) == 36_919, f"Error: vector tiene {len(vector)} features, esperados 36 919"

    return vector


def _burst_stats(valores: list) -> tuple:
    if not valores:
        return (0, 0, 0, 0, 0)
    if len(valores) == 1:
        v = valores[0]
        return (v, v, 0, v, v)
    return (
        min(valores),
        max(valores),
        statistics.stdev(valores),
        statistics.mean(valores),
        statistics.median(valores),
    )


def nombrarFicheroOW(
    pcap_file: str,
    mapeo: dict[str, str] | None = None,
    monitored_domains: set[str] | None = None,
) -> str:
    """
    Devuelve la etiqueta de un pcap para el escenario Open World.

    - Si se proporciona mapeo ({basename_pcap: dominio}) se usa el dominio
      real como etiqueta.
    - Si monitored_domains no es None, los dominios que NO estén en él
      se etiquetan como 'unknown'.
    - Si no hay mapeo disponible se cae al convenio de nombre CW:
      captura_<bloque>_<N>.pcap → pagina_<N>
    """
    basename = os.path.basename(pcap_file)

    if mapeo is not None:
        dominio = mapeo.get(basename)
        if dominio is None:
            return "unknown"
        if monitored_domains is not None and dominio not in monitored_domains:
            return "unknown"
        return dominio

    # fallback: convenio de nombre Closed World
    nombre = os.path.splitext(basename)[0]
    partes = nombre.split("_")
    bloque = partes[1]
    pagina = int(bloque[-2:])
    if pagina == 0:
        pagina = 100
    return f"pagina_{pagina}"


def procesarDirectorioOW(
    directorio: str,
    client_ip: str,
    server_ip: str,
    server_port: int,
    output_path: str,
    mapeo: dict[str, str] | None = None,
    monitored_domains: set[str] | None = None,
) -> None:

    pcaps = sorted([f for f in os.listdir(directorio) if f.endswith(".pcap")])

    if not pcaps:
        print(f"No se encontraron archivos .pcap en: {directorio}")
        return

    cabecera = ["label"] + [f"feature_{i}" for i in range(36_919)]
    errores = []

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cabecera)

        for i, nombre in enumerate(pcaps):
            pcap_path = os.path.join(directorio, nombre)
            etiqueta = nombrarFicheroOW(nombre, mapeo, monitored_domains)
            print(f"[{i+1}/{len(pcaps)}] {nombre}  →  label: '{etiqueta}'", end="", flush=True)
            try:
                # única llamada a tshark por pcap
                frames = a_ConnStats.extraer_frames_tls(pcap_path)
                vector = extraer_todas_las_features_OW(
                    frames=frames,
                    client_ip=client_ip,
                    server_ip=server_ip,
                    server_port=server_port,
                )
                writer.writerow([etiqueta] + vector)
                print("  ✓")
            except Exception as e:
                print(f"\nError procesando {nombre}: {e}")
                errores.append((nombre, str(e)))

    print(f"\nProcesamiento completado. Resultados guardados en: {output_path}")
    if errores:
        print(f"Ficheros con errores: {errores}")

if __name__ == "__main__":
    client_ip = "172.16.56.2"
    server_ip = "172.16.56.1"
    server_port = 443

    parser = argparse.ArgumentParser(
        description="Extrae features H2Classifier para escenario Open World"
    )
    parser.add_argument(
        "directorio",
        help="Ruta al directorio que contiene los archivos .pcap"
    )
    parser.add_argument(
        "--output", "-o",
        default="datos/resultados/features_OW.csv",
        help="Ruta al archivo CSV de salida"
    )
    parser.add_argument(
        "--mapeo", "-m",
        default=None,
        help="Ruta al fichero txt de metadatos OW para mapear pcap → dominio web"
    )
    parser.add_argument(
        "--monitored",
        default=None,
        help=(
            "Fichero con las URLs/dominios monitorizados (uno por línea). "
            "Los pcaps cuyo dominio no aparezca se etiquetan 'unknown'."
        )
    )
    args = parser.parse_args()

    mapeo = cargar_mapeo_pcaps(args.mapeo) if args.mapeo else None
    monitored_domains = cargar_dominios_monitorizados(args.monitored) if args.monitored else None

    output_path = args.output
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(args.directorio, f"features_OW_{timestamp}.csv")

    procesarDirectorioOW(
        directorio=args.directorio,
        client_ip=client_ip,
        server_ip=server_ip,
        server_port=server_port,
        output_path=output_path,
        mapeo=mapeo,
        monitored_domains=monitored_domains,
    )
