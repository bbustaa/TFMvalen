import statistics
import a_ConnStats


def calcular_bursts_b1(frames, client_ip, server_ip, server_port):
    """
    Bytes TLS enviados por el servidor entre dos paquetes consecutivos del cliente
    en la conexión cliente↔servidor:server_port.

    Acepta frames ya extraídos (lista devuelta por a_ConnStats.extraer_frames_tls).
    """
    bursts = []
    burst_actual = 0
    visto_cliente = False

    for frame in frames:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        src_port = frame["src_port"]
        dst_port = frame["dst_port"]
        record_lengths = frame["record_lengths"]

        if not record_lengths:
            continue

        conexion = (
            (ip_src == client_ip and dst_port == str(server_port)) or
            (ip_dst == client_ip and src_port == str(server_port))
        )

        if not conexion:
            continue

        if ip_src == client_ip:
            if visto_cliente:
                bursts.append(burst_actual)
            burst_actual = 0
            visto_cliente = True
        else:
            if visto_cliente:
                burst_actual += sum(record_lengths)

    return bursts


def calcular_estadisticas(valores):

    if not valores:
        return {"min": 0, "max": 0, "mean": 0, "std": 0, "median": 0}

    if len(valores) == 1:
        v = valores[0]
        return {"min": v, "max": v, "mean": v, "std": 0, "median": v}

    return {
        "min": min(valores),
        "max": max(valores),
        "mean": statistics.mean(valores),
        "std": statistics.stdev(valores),
        "median": statistics.median(valores),
    }


def imprimir_resultados(bursts):

    print(f"\n")
    print("Lista de bursts:")
    print(bursts)
    print(f"\nNúmero de bursts: {len(bursts)}")
    print(f"Bursts iguales a 0: {bursts.count(0)}")

    stats = calcular_estadisticas(bursts)
    print("\nEstadísticas:")
    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    pcap_file = r"datos/escenario1/captura_10000_10000.pcap"
    client_ip = "10.6.56.13"
    server_ip = ""
    server_port = 443

    frames = a_ConnStats.extraer_frames_tls(pcap_file)
    bursts = calcular_bursts_b1(frames, client_ip, server_ip, server_port)
    imprimir_resultados(bursts)
