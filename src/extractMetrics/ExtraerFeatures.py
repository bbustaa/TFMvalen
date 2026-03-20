import subprocess
import statistics
import argparse
from collections import defaultdict, Counter
import os
from datetime import datetime

TSHARK_PATH = r"C:\Program Files\Wireshark\tshark.exe"
MAX_TLS_RECORD_SIZE = 18432
BURST_BLOCK_SIZE = 20


#  PRIMER PASO --> EXTRACCIÓN

def extraer_frames_tls(pcap_file: str) -> list[dict]:

    # Ejecuta tshark para extraer solo los frames TLS con los campos necesarios para el análisis
    # estamos mejorando la eficiencia del código respecto a las versiones en /featuresH2C/ al extraer todo de una vez, 
    # evitando múltiples llamadas a tshark  y múltiples lecturas del pcap (y menos ahora que no usamos pyshark)

    cmd = [
        TSHARK_PATH,
        "-r", pcap_file,
        "-Y", "tls",
        "-T", "fields",
        "-e", "frame.number",
        "-e", "frame.time_epoch",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "tcp.srcport",
        "-e", "tcp.dstport",
        "-e", "tls.record.length",
        "-E", "header=n",
        "-E", "separator=\t",
        "-E", "occurrence=a",
        "-E", "aggregator=,",
    ]

    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)

    #lLista donde se va a almacenara la información procesada de cada frame TLS    
    frames = []
    # procesa la salida línea por línea --> c/u línea representa un frame TLS de la captura
    for linea in resultado.stdout.splitlines():
        partes = linea.split("\t")
        # si faltan campos, se ignora la línea para evitar errores
        if len(partes) < 7:
            continue

        # se desempaquetan los campos extraídos por tshark
        frame_number, timestamp, ip_src, ip_dst, src_port, dst_port, lengths_str = partes[:7]

        # aquí se van a almacenar los tamaños de las longitudes de los records TLS encontrados en el frame
        record_lengths = []
        # si el campo de longitudes no está vacío --> se procesan separados por comas
        # PROBLEMA DEL PYSHARK --> pueden haber varios records TLS en un mismo frame y tshark los devuelve separados por comas
        if lengths_str.strip():
            for v in lengths_str.split(","):
                v = v.strip()
                if v.isdigit():
                    record_lengths.append(int(v))

        # conversión de tipos y almacenamiento estructurado del frame --> i algún campo numérico no puede convertirse 
        # correctamente --> se descarta la línea
        try:
            frames.append({
                "frame_number": int(frame_number),
                "timestamp":    float(timestamp),
                "ip_src":       ip_src,
                "ip_dst":       ip_dst,
                "src_port":     src_port,
                "dst_port":     dst_port,
                "record_lengths": record_lengths,
            })
        except ValueError:
            continue

    return frames


# ─────────────────────────────────────────────
#  2. PASE ÚNICO: acumula todo en una pasada
# ─────────────────────────────────────────────

def _stats5(valores: list) -> tuple:
    """Devuelve (min, max, std, mean, median). Si está vacío devuelve ceros."""
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


def extraer_todas_las_features(
    pcap_file: str,
    client_ip: str,
    server_ip: str,
    server_port: int,
) -> list:
    """
    Extrae el vector completo de 36,919 features en un único pase sobre los frames TLS.

    Parámetros
    ----------
    pcap_file   : ruta al archivo .pcap
    client_ip   : IP del cliente
    server_ip   : IP del servidor (necesaria para bursts y secuencia)
    server_port : puerto del servidor (normalmente 443)

    Retorna
    -------
    list de 36,919 valores numéricos
    """
    frames = extraer_frames_tls(pcap_file)

    # ── Acumuladores globales (features a, c, e) ──────────────────────────
    total_incoming_records = 0
    total_outgoing_records = 0
    total_tls_bytes = 0

    incoming_sizes: list[int] = []   # todos los tamaños TLS incoming
    outgoing_sizes: list[int] = []   # todos los tamaños TLS outgoing

    incoming_freq = [0] * MAX_TLS_RECORD_SIZE
    outgoing_freq = [0] * MAX_TLS_RECORD_SIZE

    # ── Acumuladores de burst método 1 ───────────────────────────────────
    # Solo para la conexión (client_ip, server_ip, server_port)
    bursts_m1: list[int] = []
    burst_actual = 0
    visto_primer_cliente = False

    # ── Acumuladores de burst método 2 ───────────────────────────────────
    # Secuencia de (origen: 'S'/'C', num_records) para la conexión
    # Usamos lista de tuplas en lugar de listas de strings → menos memoria
    secuencia: list[tuple[str, int]] = []   # ('S'|'C', num_records)

    # ─────────────────────────────────────────────────────────────────────
    for frame in frames:
        ip_src         = frame["ip_src"]
        ip_dst         = frame["ip_dst"]
        src_port       = frame["src_port"]
        dst_port       = frame["dst_port"]
        record_lengths = frame["record_lengths"]

        if not record_lengths:
            continue

        num_records = len(record_lengths)

        # ── Determinar dirección respecto al cliente (features a, c, e) ──
        participates_globally = (ip_src == client_ip or ip_dst == client_ip)
        if participates_globally:
            total_tls_bytes += sum(record_lengths)

            if ip_src == client_ip:
                total_outgoing_records += num_records
                outgoing_sizes.extend(record_lengths)
                for tam in record_lengths:
                    if 1 <= tam <= MAX_TLS_RECORD_SIZE:
                        outgoing_freq[tam - 1] += 1
            else:
                total_incoming_records += num_records
                incoming_sizes.extend(record_lengths)
                for tam in record_lengths:
                    if 1 <= tam <= MAX_TLS_RECORD_SIZE:
                        incoming_freq[tam - 1] += 1

        # ── Burst método 1 y secuencia método 2 (solo la conexión target) ──
        pertenece_conexion = (
            (ip_src == client_ip and ip_dst == server_ip and dst_port == str(server_port)) or
            (ip_src == server_ip and ip_dst == client_ip and src_port == str(server_port))
        )

        if pertenece_conexion:
            if ip_src == client_ip:
                # Paquete del cliente → cierra burst anterior
                if visto_primer_cliente:
                    bursts_m1.append(burst_actual)
                burst_actual = 0
                visto_primer_cliente = True
                secuencia.append(("C", num_records))
            else:
                # Paquete del servidor → acumula en burst actual
                if visto_primer_cliente:
                    burst_actual += sum(record_lengths)
                secuencia.append(("S", num_records))

    # ── Calcular burst método 2: bloques de BURST_BLOCK_SIZE records ──────
    # Expandimos solo los conteos, no los strings
    bloques_m2: list[int] = []
    bloque_count = 0
    bloque_servidor = 0

    for origen, n in secuencia:
        restante = n
        while restante > 0:
            espacio = BURST_BLOCK_SIZE - bloque_count
            tomar = min(restante, espacio)

            if origen == "S":
                bloque_servidor += tomar

            bloque_count += tomar
            restante -= tomar

            if bloque_count == BURST_BLOCK_SIZE:
                bloques_m2.append(bloque_servidor)
                bloque_count = 0
                bloque_servidor = 0

    # ── Top-20 tamaños menos frecuentes ───────────────────────────────────
    def top20_menos_frecuentes(sizes: list[int]) -> list[int]:
        if not sizes:
            return [0] * 20
        contador = Counter(sizes)
        ordenados = sorted(contador.items(), key=lambda x: (x[1], x[0]))
        top20 = [tam for tam, _ in ordenados[:20]]
        while len(top20) < 20:
            top20.append(0)
        return top20

    incoming_top20 = top20_menos_frecuentes(incoming_sizes)
    outgoing_top20 = top20_menos_frecuentes(outgoing_sizes)

    # ── Estadísticas ───────────────────────────────────────────────────────
    min_b1, max_b1, std_b1, mean_b1, med_b1 = _stats5(bursts_m1)
    min_b2, max_b2, std_b2, mean_b2, med_b2 = _stats5(bloques_m2)

    num_incoming_diff = len(set(incoming_sizes))
    num_outgoing_diff = len(set(outgoing_sizes))

    # ── Ensamblar vector ───────────────────────────────────────────────────
    vector = []

    # (a) Connection stats [0..2]
    vector += [total_incoming_records, total_outgoing_records, total_tls_bytes]

    # (b) Burst method 1 [3..7]
    vector += [min_b1, max_b1, std_b1, mean_b1, med_b1]

    # (b) Burst method 2 [8..12]
    vector += [min_b2, max_b2, std_b2, mean_b2, med_b2]

    # (c) Count different sizes [13..14]
    vector += [num_incoming_diff, num_outgoing_diff]

    # (d) 20 less used record sizes incoming [15..34]
    vector += incoming_top20

    # (d) 20 less used record sizes outgoing [35..54]
    vector += outgoing_top20

    # (e) Incoming size frequency [55..18486]
    vector += incoming_freq

    # (e) Outgoing size frequency [18487..36918]
    vector += outgoing_freq

    assert len(vector) == 36_919, f"Error: vector tiene {len(vector)} features, esperados 36,919"

    return vector


# ─────────────────────────────────────────────
#  3. UTILIDADES DE INSPECCIÓN
# ─────────────────────────────────────────────

def imprimir_resumen(vector: list) -> None:
    """Muestra un resumen legible del vector sin imprimir las 36k dimensiones."""
    print("=" * 60)
    print("H2CLASSIFIER FEATURE VECTOR — RESUMEN")
    print("=" * 60)
    print(f"Longitud total del vector: {len(vector)}")
    print()

    print("── (a) Connection statistics ────────────────────────────")
    print(f"  [0]  incoming records   : {vector[0]}")
    print(f"  [1]  outgoing records   : {vector[1]}")
    print(f"  [2]  total TLS bytes    : {vector[2]}")
    print()

    print("── (b) Burst method 1 ───────────────────────────────────")
    labels = ["min", "max", "std", "mean", "median"]
    for i, lbl in enumerate(labels):
        print(f"  [{3+i}]  {lbl:10s}: {vector[3+i]:.4f}")
    print()

    print("── (b) Burst method 2 ───────────────────────────────────")
    for i, lbl in enumerate(labels):
        print(f"  [{8+i}]  {lbl:10s}: {vector[8+i]:.4f}")
    print()

    print("── (c) Count different sizes ────────────────────────────")
    print(f"  [13] incoming diff sizes: {vector[13]}")
    print(f"  [14] outgoing diff sizes: {vector[14]}")
    print()

    print("── (d) 20 less used sizes (incoming) [15..34] ───────────")
    print(f"  {vector[15:35]}")
    print("── (d) 20 less used sizes (outgoing) [35..54] ───────────")
    print(f"  {vector[35:55]}")
    print()

    incoming_nz = [(i+1, v) for i, v in enumerate(vector[55:18487]) if v > 0]
    outgoing_nz = [(i+1, v) for i, v in enumerate(vector[18487:36919]) if v > 0]
    print("── (e) Incoming size frequency [55..18486] ──────────────")
    print(f"  Tamaños con frecuencia > 0: {len(incoming_nz)}")
    print(f"  {dict(incoming_nz)}")
    print("── (e) Outgoing size frequency [18487..36918] ───────────")
    print(f"  Tamaños con frecuencia > 0: {len(outgoing_nz)}")
    print(f"  {dict(outgoing_nz)}")


if __name__ == "__main__":

    client_ip = "172.16.56.2"
    server_ip = "172.16.56.1"
    server_port = 443

    parser = argparse.ArgumentParser(
        description= "Extrae el vector de features H2Classifier de un archivo PCAP"
    )
    parser.add_argument(
        "pcap",
        help="Ruta al archivo .pcap"
    )
    args = parser.parse_args()

    vector = extraer_todas_las_features(
        pcap_file=args.pcap,
        client_ip=client_ip,
        server_ip=server_ip,
        server_port=server_port,
    )

    imprimir_resumen(vector)

    # Crear carpeta de salida si no existe
    output_dir = "resultados"
    os.makedirs(output_dir, exist_ok=True)

    # Guardamos el el resultado en un CSV con nombre basado en el pcap y timestamp
    nombre_base = os.path.splitext(os.path.basename(args.pcap))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"{nombre_base}_{timestamp}.csv")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(",".join(map(str, vector)) + "\n")

    print(f"\nVector guardado en: {output_path}")