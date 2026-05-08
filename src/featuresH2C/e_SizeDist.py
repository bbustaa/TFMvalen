import a_ConnStats

MAX_TLS_RECORD_SIZE = 18432


def calcular_distribucion_from_frames(frames, client_ip):
    """
    Calcula (incoming_freq, outgoing_freq) a partir de frames ya extraídos.
    Cada lista tiene MAX_TLS_RECORD_SIZE = 18432 posiciones.
    """
    incoming_freq = [0] * MAX_TLS_RECORD_SIZE
    outgoing_freq = [0] * MAX_TLS_RECORD_SIZE

    for frame in frames:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        record_lengths = frame["record_lengths"]

        if ip_src != client_ip and ip_dst != client_ip:
            continue

        for tam in record_lengths:
            if not (1 <= tam <= MAX_TLS_RECORD_SIZE):
                continue
            indice = tam - 1
            if ip_src == client_ip:
                outgoing_freq[indice] += 1
            else:
                incoming_freq[indice] += 1

    return incoming_freq, outgoing_freq


def calcular_distribucion_tamanos_tls(pcap_file, client_ip):
    """
    Calcula la distribución de tamaños de TLS records para tráfico incoming y outgoing --> vector con las frecuencias de todos
    los tamaños posibles entre 1 y MAX_TLS_RECORD_SIZE = 18432
    """
    incoming_freq = [0] * MAX_TLS_RECORD_SIZE
    outgoing_freq = [0] * MAX_TLS_RECORD_SIZE

    frames_tls = a_ConnStats.extraer_info_tls_por_frame(pcap_file)

    for frame in frames_tls:
        ip_src = frame["ip_src"]
        ip_dst = frame["ip_dst"]
        record_lengths = frame["record_lengths"]

        # Solo consideramos tráfico donde participe el cliente
        if ip_src != client_ip and ip_dst != client_ip:
            continue

        for tam in record_lengths:
            # Solo consideramos tamaños válidos del rango definido
            if not (1 <= tam <= MAX_TLS_RECORD_SIZE):
                continue

            indice = tam - 1

            if ip_src == client_ip:
                # Cliente -> servidor = outgoing
                outgoing_freq[indice] += 1
            else:
                # Servidor -> cliente = incoming
                incoming_freq[indice] += 1

    return {
        "incoming_size_distribution": incoming_freq,
        "outgoing_size_distribution": outgoing_freq
    }


def obtener_indices_no_cero(vector):
    """
    Devuelve un diccionario {tamano: frecuencia} solo con las entradas no nulas --> para que no sea un tocho print 
    y visualizar mejor
    """
    return {i + 1: freq for i, freq in enumerate(vector) if freq > 0}


def imprimir_resumen(resultados):

    incoming = resultados["incoming_size_distribution"]
    outgoing = resultados["outgoing_size_distribution"]

    incoming_no_cero = obtener_indices_no_cero(incoming)
    outgoing_no_cero = obtener_indices_no_cero(outgoing)

    print("\n")
    print(f"Tamaños incoming observados: {len(incoming_no_cero)}")
    print(f"Tamaños outgoing observados: {len(outgoing_no_cero)}")

    print("\nFrecuencias incoming de tamaños dif a cero:")
    print(incoming_no_cero)

    print("\nFrecuencias outgoing de tamaños dif a cero:")
    print(outgoing_no_cero)


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"

    resultados = calcular_distribucion_tamanos_tls(pcap_file, client_ip)
    imprimir_resumen(resultados)