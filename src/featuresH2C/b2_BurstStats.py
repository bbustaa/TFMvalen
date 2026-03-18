import statistics
import a_ConnStats


def construir_secuencia_tls_por_conexion(pcap_file, client_ip, server_ip, server_port):
    """
    Construye la secuencia temporal de TLS records de una conexión.

    Cada TLS record se representa como:
    - "S" si fue enviado por el servidor
    - "C" si fue enviado por el cliente

    Si un frame contiene varios TLS records, se añaden tantas marcas
    como records haya en ese frame, respetando el orden temporal del PCAP.
    """
    frames_tls = a_ConnStats.extraer_info_tls_por_frame(pcap_file)
    secuencia = []

    for frame in frames_tls:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        src_port = frame["src_port"]
        dst_port = frame["dst_port"]
        record_lengths = frame["record_lengths"]

        # Nos quedamos solo con la conexión concreta
        pertenece = (
            (ip_src == client_ip and ip_dst == server_ip and dst_port == str(server_port)) or
            (ip_src == server_ip and ip_dst == client_ip and src_port == str(server_port))
        )

        if not pertenece:
            continue

        num_records = len(record_lengths)
        if num_records == 0:
            continue

        # Añadimos una marca por cada TLS record del frame
        if ip_src == server_ip:
            secuencia.extend(["S"] * num_records)
        elif ip_src == client_ip:
            secuencia.extend(["C"] * num_records)

    return secuencia


def calcular_num_records_servidor_por_bloques_de_20(pcap_file, client_ip, server_ip, server_port):
    """
    - se toma la secuencia total de TLS records de la conexión
    - se divide en bloques NO solapados de 20 records
    - para cada bloque se cuenta cuántos records fueron enviados por el servidor

    Como son ventanas de 20 records TLS --> último bloque incompleto se descarta
    """
    secuencia = construir_secuencia_tls_por_conexion(
        pcap_file,
        client_ip,
        server_ip,
        server_port
    )

    valores = []

    # Bloques no solapados de 20 TLS records
    for i in range(0, len(secuencia), 20):
        bloque = secuencia[i:i + 20]

        # Solo usamos bloques completos de 20
        if len(bloque) < 20:
            break

        num_servidor = bloque.count("S")
        valores.append(num_servidor)

    return valores


def calcular_estadisticas(valores):

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


def imprimir_resultados(valores):

    print("\nMétodo 2 - número de TLS records del servidor en cada bloque de 20:")
    print(valores)
    print(f"Número de ventanas completas: {len(valores)}")
    print(f"Valores iguales a 0: {valores.count(0)}")

    stats = calcular_estadisticas(valores)

    print("\nEstadísticas:")
    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"
    server_ip = "172.16.56.1"
    server_port = 443

    valores = calcular_num_records_servidor_por_bloques_de_20(
        pcap_file,
        client_ip,
        server_ip,
        server_port
    )

    imprimir_resultados(valores)