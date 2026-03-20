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

#  SEGUNDO PASO --> Definición de funciones auxiliares 
#  necesarias para la extracción de features

def burstStats(valores: list) -> tuple:
    
    # con el conjunto/set de valores:
    # 1. bytes TLS enviados por el servidor entre dos paquetes enviados por el cliente 
    # 2. TLS records del servidor cada 20 TLS records tanto incoming como outcoming
    # --> calcula las 5 estadísticas dichas en el paper --> mín, máx, std, media y mediana
    # si en ese conjunto/set de datos es cero --> devuelve ceros
    
    if not valores:
        return (0, 0, 0, 0, 0)
    # Para el caso que solo sea un valor en el conjunto :)
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

def top20Sizes(sizes: list[int]) -> list[int]:
    
    # con el conjunto/set de tamaños de TLS records --> devuelve los 20 tamaños menos frecuentes --> 
    # ordenados por frecuencia y en caso de empate por tamaño

    if not sizes:
        return [0] * 20

    contador = Counter(sizes)
    ordenados = sorted(contador.items(), key=lambda x: (x[1], x[0]))
    top20 = [tam for tam, _ in ordenados[:20]]

    while len(top20) < 20:
        top20.append(0)

    return top20

if __name__ == "__main__":

    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"

    frames = extraer_frames_tls(pcap_file)

    # Construimos una lista con todos los tamaños de TLS records del pcap
    todos_los_records = []
    for frame in frames:
        todos_los_records.extend(frame["record_lengths"])

    stats = burstStats(todos_los_records)
    sizes = top20Sizes(todos_los_records)
    
    # hacemos una pruebita de que esto funcione :)

    print(f"Número de frames TLS encontrados: {len(frames)}")
    # cada tamaño corrssponde a un TLS record
    print(f"Número total de TLS records encontrados: {len(todos_los_records)}")

    # hacemos los calculos de todos los valores de la captura
    print("\nResultado de burstStats(valores):")
    print(f"Mínimo: {stats[0]}")
    print(f"Máximo: {stats[1]}")
    print(f"Desviación típica: {stats[2]}")
    print(f"Media: {stats[3]}")
    print(f"Mediana: {stats[4]}")
    print("\nResultado de top20Sizes(sizes):")
    print(f"Top 20 tamaños TLS menos frecuentes: {sizes}")