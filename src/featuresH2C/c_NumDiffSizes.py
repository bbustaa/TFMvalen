import a_ConnStats


def obtener_tamanos_from_frames(frames, client_ip):
    """
    Devuelve (incoming_sizes, outgoing_sizes) a partir de frames ya extraídos.
    """
    incoming_sizes = []
    outgoing_sizes = []

    for frame in frames:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        record_lengths = frame["record_lengths"]

        if ip_src != client_ip and ip_dst != client_ip:
            continue
        if not record_lengths:
            continue

        if ip_src == client_ip:
            outgoing_sizes.extend(record_lengths)
        else:
            incoming_sizes.extend(record_lengths)

    return incoming_sizes, outgoing_sizes


def obtener_tamanos_tls_incoming_outgoing(pcap_file, client_ip):
    """
    Devuelve dos listas con todos los tamaños de TLS records:
    incoming y outgoing.
    """
    incoming_sizes = []
    outgoing_sizes = []

    frames = a_ConnStats.extraer_info_tls_por_frame(pcap_file)

    for frame in frames:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        record_lengths = frame["record_lengths"]

        if ip_src != client_ip and ip_dst != client_ip:
            continue

        if not record_lengths:
            continue

        if ip_src == client_ip:
            outgoing_sizes.extend(record_lengths)
        else:
            incoming_sizes.extend(record_lengths)

    return incoming_sizes, outgoing_sizes


def contar_numero_tamanos_tls_distintos(pcap_file, client_ip):
    """
    Devuelve el número de tamaños distintos de TLS records
    para incoming y outgoing.
    """
    incoming_sizes, outgoing_sizes = obtener_tamanos_tls_incoming_outgoing(pcap_file, client_ip)

    incoming_set = set(incoming_sizes)
    outgoing_set = set(outgoing_sizes)

    return {
        "incoming_num_different_tls_sizes": len(incoming_set),
        "outgoing_num_different_tls_sizes": len(outgoing_set),
        "incoming_sizes": sorted(incoming_set),
        "outgoing_sizes": sorted(outgoing_set)
    }


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"

    resultados = contar_numero_tamanos_tls_distintos(pcap_file, client_ip)

    print("\n")
    print(f"Tamaños diferentes en incoming: {resultados['incoming_num_different_tls_sizes']}")
    print(f"Tamaños diferentes en outgoing: {resultados['outgoing_num_different_tls_sizes']}")

    print("\nTamaños incoming:")
    print(resultados["incoming_sizes"])

    print("\nTamaños outgoing:")
    print(resultados["outgoing_sizes"])