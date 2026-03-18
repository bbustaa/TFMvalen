from collections import Counter
import c_NumDiffSizes


def obtener_20_tamanos_menos_frecuentes(lista_tamanos):
    """
    Devuelve los 20 tamaños TLS menos frecuentes de una lista.

    Criterio de ordenación:
    1. Menor frecuencia primero.
    2. En caso de empate, menor tamaño primero.

    Si hay menos de 20 tamaños distintos, se rellena con ceros.
    """
    contador = Counter(lista_tamanos)

    # Cada elemento es una tupla: (tamano, frecuencia)
    # Ordenamos por frecuencia ascendente y, en empate, por tamaño ascendente
    ordenados = sorted(contador.items(), key=lambda x: (x[1], x[0]))

    # Nos quedamos solo con los tamaños
    top20 = [tamano for tamano, _ in ordenados[:20]]

    # Relleno hasta 20 valores si no hay suficientes tamaños distintos
    while len(top20) < 20:
        top20.append(0)

    return top20


def obtener_top_20_sizes_representativos(pcap_file, client_ip):
    """
    Calcula los 20 tamaños TLS menos frecuentes en tráfico incoming
    y los 20 menos frecuentes en tráfico outgoing.
    """
    incoming_sizes, outgoing_sizes = c_NumDiffSizes.obtener_tamanos_tls_incoming_outgoing(
        pcap_file,
        client_ip
    )

    incoming_top20 = obtener_20_tamanos_menos_frecuentes(incoming_sizes)
    outgoing_top20 = obtener_20_tamanos_menos_frecuentes(outgoing_sizes)

    return {
        "incoming_top20_sizes": incoming_top20,
        "outgoing_top20_sizes": outgoing_top20
    }


if __name__ == "__main__":
    pcap_file = r"datos\escenario1\captura_10000_10000.pcap"
    client_ip = "172.16.56.2"

    resultados = obtener_top_20_sizes_representativos(pcap_file, client_ip)

    print("Top 20 tamaños menos frecuentes en incoming:")
    print(resultados["incoming_top20_sizes"])

    print("\nTop 20 tamaños menos frecuentes en outgoing:")
    print(resultados["outgoing_top20_sizes"])