import pyshark
import statistics
import a_ConnStats


def construir_mapa_tamanos_tls_por_frame(pcap_file):
    """
    Construye un diccionario --> numero_de_frame -> lista de tamaños TLS de ese frame
    """
    frames_tls = a_ConnStats.extraer_info_tls_por_frame(pcap_file)

    mapa = {}
    for frame in frames_tls:
        mapa[frame["frame_number"]] = frame["record_lengths"]

    return mapa


def paquete_pertenece_a_conexion(packet, client_ip, server_ip, server_port):
    """
    Comprueba si el paquete pertenece a la conexión cliente-servidor.
    """
    if not hasattr(packet, "ip") or not hasattr(packet, "tcp"):
        return False

    ip_src = packet.ip.src
    ip_dst = packet.ip.dst
    src_port = packet.tcp.srcport
    dst_port = packet.tcp.dstport

    return (
        (ip_src == client_ip and ip_dst == server_ip and dst_port == str(server_port)) or
        (ip_src == server_ip and ip_dst == client_ip and src_port == str(server_port))
    )


def es_paquete_cliente(packet, client_ip):
    """
    Devuelve True si el paquete sale del cliente.
    """
    return hasattr(packet, "ip") and packet.ip.src == client_ip


def es_paquete_servidor(packet, server_ip):
    """
    Devuelve True si el paquete sale del servidor.
    """
    return hasattr(packet, "ip") and packet.ip.src == server_ip


def obtener_tamanos_tls_del_frame(packet, mapa_tls_por_frame):
    """
    Devuelve la lista de tamaños TLS asociados al frame actual.
    """
    try:
        frame_number = int(packet.number)
        return mapa_tls_por_frame.get(frame_number, [])
    except Exception:
        return []


def calcular_bursts(pcap_file, client_ip, server_ip, server_port):
    """
    Primer método de burst:
    se acumulan los bytes enviados por el servidor entre dos paquetes
    consecutivos enviados por el cliente + cualquier paquete del cliente cierra el burst --> ACKs, aplicación, TLS...
    """
    bursts = []
    burst_actual = 0
    hemos_visto_primer_paquete_cliente = False

    mapa_tls_por_frame = construir_mapa_tamanos_tls_por_frame(pcap_file)

    cap = pyshark.FileCapture(
        pcap_file,
        keep_packets=False
    )

    for packet in cap:
        try:
            if not paquete_pertenece_a_conexion(packet, client_ip, server_ip, server_port):
                continue

            # Cada paquete del cliente cierra el burst anterior
            if es_paquete_cliente(packet, client_ip):
                if hemos_visto_primer_paquete_cliente:
                    bursts.append(burst_actual)

                burst_actual = 0
                hemos_visto_primer_paquete_cliente = True

            # Si el paquete es del servidor, acumulamos sus bytes TLS
            elif es_paquete_servidor(packet, server_ip):
                if not hemos_visto_primer_paquete_cliente:
                    continue

                tls_lengths = obtener_tamanos_tls_del_frame(packet, mapa_tls_por_frame)
                burst_actual += sum(tls_lengths)

        except Exception as e:
            print(f"Error procesando paquete {getattr(packet, 'number', '?')}: {e}")

    cap.close()
    return bursts


def calcular_estadisticas(valores):
    """
    Calcula mínimo, máximo, media, desviación típica y mediana.
    """
    if not valores:
        return {
            "min": 0,
            "max": 0,
            "mean": 0,
            "std": 0,
            "median": 0
        }

    if len(valores) == 1:
        v = valores[0]
        return {
            "min": v,
            "max": v,
            "mean": v,
            "std": 0,
            "median": v
        }

    return {
        "min": min(valores),
        "max": max(valores),
        "mean": statistics.mean(valores),
        "std": statistics.stdev(valores),
        "median": statistics.median(valores)
    }


def imprimir_resultados(bursts):
    """
    Imprime la lista de bursts y sus estadísticas.
    """
    print(f"\n")
    print("Lista de bursts:")
    print(bursts)
    print("\n")
    print(f"Número de bursts: {len(bursts)}")
    print(f"Bursts iguales a 0: {bursts.count(0)}")

    stats = calcular_estadisticas(bursts)
    print("\nEstadísticas:")
    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"
    server_ip = "172.16.56.1"
    server_port = 443

    bursts = calcular_bursts(
        pcap_file,
        client_ip,
        server_ip,
        server_port
    )

    imprimir_resultados(bursts)