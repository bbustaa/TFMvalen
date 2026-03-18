import subprocess
from collections import defaultdict

TSHARK_PATH = r"C:\Program Files\Wireshark\tshark.exe"


def extraer_info_tls_por_frame(pcap_file):
    """
    Extrae información TLS de cada frame del PCAP usando TShark.
    """

    cmd = [
        TSHARK_PATH,
        "-r", pcap_file,
        "-Y", "tls",
        "-T", "fields",
        "-e", "frame.number",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "tcp.srcport",
        "-e", "tcp.dstport",
        "-e", "tls.record.length",
        "-E", "header=n",
        "-E", "separator=\t",
        "-E", "occurrence=a",
        "-E", "aggregator=,"
    ]

    resultado = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    frames = []

    for linea in resultado.stdout.splitlines():
        partes = linea.split("\t")

        if len(partes) < 6:
            continue

        frame_number, ip_src, ip_dst, src_port, dst_port, lengths_str = partes[:6]

        record_lengths = []

        if lengths_str.strip():
            for valor in lengths_str.split(","):
                valor = valor.strip()
                if valor.isdigit():
                    record_lengths.append(int(valor))

        frames.append({
            "frame_number": int(frame_number),
            "ip_src": ip_src,
            "ip_dst": ip_dst,
            "src_port": src_port,
            "dst_port": dst_port,
            "record_lengths": record_lengths
        })

    return frames


def contar_tls_records_por_conexion(pcap_file, client_ip):
    """
    Cuenta estadísticas TLS por conexión en la que participa el cliente --> incoming/outgoing tls records
    y total de bytes TLS por conexión
    """

    stats = defaultdict(lambda: {
        "incoming_records": 0,
        "outgoing_records": 0,
        "total_tls_bytes": 0
    })

    frames = extraer_info_tls_por_frame(pcap_file)

    for frame in frames:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        src_port = frame["src_port"]
        dst_port = frame["dst_port"]
        record_lengths = frame["record_lengths"]

        # Solo nos interesan frames donde participa el cliente
        if ip_src != client_ip and ip_dst != client_ip:
            continue

        # El número de records TLS del paquete es el número de tamaños extraídos
        num_records = len(record_lengths)

        if num_records == 0:
            continue

        # Suma de los tamaños de los TLS records del paquete
        total_packet_tls_bytes = sum(record_lengths)

        # Normalizamos la clave para que siempre quede:
        # (server_ip, server_port, client_ip, client_port)
        if ip_src == client_ip:
            # Paquete saliente del cliente al servidor
            conn_key = (ip_dst, dst_port, ip_src, src_port)
            stats[conn_key]["outgoing_records"] += num_records
        else:
            # Paquete entrante del servidor al cliente
            conn_key = (ip_src, src_port, ip_dst, dst_port)
            stats[conn_key]["incoming_records"] += num_records

        stats[conn_key]["total_tls_bytes"] += total_packet_tls_bytes

    return stats


def imprimir_resultados(stats):
    
    print(f"Conexiones TLS encontradas: {len(stats)}\n")

    for (server_ip, server_port, client_ip, client_port), valores in sorted(stats.items()):
        print(
            f"{server_ip}:{server_port} <-> {client_ip}:{client_port} | "
            f"incoming_records={valores['incoming_records']} | "
            f"outgoing_records={valores['outgoing_records']} | "
            f"total_tls_bytes={valores['total_tls_bytes']}"
        )


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"

    stats = contar_tls_records_por_conexion(pcap_file, client_ip)
    imprimir_resultados(stats)