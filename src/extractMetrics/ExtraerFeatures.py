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

# TERCER PASO --> Extraer los features

def extraer_todas_las_features(
    pcap_file: str,
    client_ip: str,
    server_ip: str,
    server_port: int,
) -> list:
    
    # para la extracción de las features necesitamos
    # el pcap, las ips (cliente y servidor), y el puerto del servidor
    # el vectore de features --> 36919 valores numéricos por cada conexión TLS
    
    frames = extraer_frames_tls(pcap_file)
    
    # PARA LOS FEATURES A, C y E --> conexiones TLS entre cliente y servidor?
    
    total_incoming_records = 0
    total_outgoing_records = 0
    total_tls_bytes = 0
    
    incoming_sizes: list[int] = []      # todos los tamaños TLS incoming
    outgoing_sizes: list[int] = []      # todos los tamaños TLS outgoing
    
    incoming_freq = [0] * MAX_TLS_RECORD_SIZE
    outgoing_freq = [0] * MAX_TLS_RECORD_SIZE   # dos listas de 18432 elementos
    
    #PARA LOS FEATURES B1 y B2 --> burstStats 
    
    burst_b1: list[int] = []  # bytes TLS enviados por el servidor entre dos paquetes enviados por el cliente
    burst_actual = 0
    visto_cliente = False
    
    secuencia: list[tuple[str, int]] = []  # Secuencia de (origen: 'S'/'C', num_records) para la conexión
    
    for frame in frames:
        
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        src_port = frame["src_port"]
        dst_port = frame["dst_port"]
        record_lengths = frame["record_lengths"]
        
        # verificar si el frame corresponde al record TLS
        # de la conexión entre el cliente y el servidor
        if not record_lengths:
            continue
        
        # cada tamaño representa un record TLS
        total_records = len(record_lengths)
        
        # para los features A, C y E --> hay que determinar si el tráfico es incoming o outgoing
        # comprobamos si en la conexión participa el cliente
        participa = (ip_src == client_ip or ip_dst == client_ip)
        if participa:
            total_tls_bytes += sum(record_lengths)
        
        # dirección outgoing    
        if ip_src == client_ip:
            # feature A
            total_outgoing_records += total_records
            outgoing_sizes.extend(record_lengths)
            # feature D
            # por cada tamaño de record TLS
            for r in record_lengths:
                # comprobamos que esté dentro del rango permitido
                if 1 <= r <= MAX_TLS_RECORD_SIZE:
                    # aumentamos en 1 la frec del tamaño r en outgoing_freq
                    outgoing_freq[r - 1] += 1
            
        else:
            # feature A
            total_incoming_records += total_records
            incoming_sizes.extend(record_lengths)
            # feature D
            for r in record_lengths:
                if 1 <= r <= MAX_TLS_RECORD_SIZE:
                    incoming_freq[r - 1] += 1
            
# para comprobar que esta parte funciona
    return {
        "total_incoming_records": total_incoming_records,
        "total_outgoing_records": total_outgoing_records,
        "total_tls_bytes": total_tls_bytes,
        "incoming_sizes": incoming_sizes,
        "outgoing_sizes": outgoing_sizes,
        "incoming_freq": incoming_freq,
        "outgoing_freq": outgoing_freq,
        "top 20 incoming sizes": top20Sizes(incoming_sizes),
        "top 20 outgoing sizes": top20Sizes(outgoing_sizes)
    }


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"
    server_ip = "172.16.56.1"
    server_port = 443

    resultado = extraer_todas_las_features(
        pcap_file=pcap_file,
        client_ip=client_ip,
        server_ip=server_ip,
        server_port=server_port,
    )
    
    print("Total incoming records:", resultado["total_incoming_records"])
    print("Total outgoing records:", resultado["total_outgoing_records"])
    print("Total TLS bytes:", resultado["total_tls_bytes"])
    print("Primeros 10 tamaños TLS incoming:", resultado["incoming_sizes"][:10])
    print("Primeros 10 tamaños TLS outgoing:", resultado["outgoing_sizes"][:10])
    print("Frecuencia de tamaños TLS incoming (primeros 10):", resultado["incoming_freq"][:10])
    print("Frecuencia de tamaños TLS outgoing (primeros 10):", resultado["outgoing_freq"][:10])
    print("Top 20 tamaños menos frecuentes incoming:", resultado["top 20 incoming sizes"])
    print("Top 20 tamaños menos frecuentes outgoing:", resultado["top 20 outgoing sizes"])