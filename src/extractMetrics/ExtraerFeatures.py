import csv
import subprocess
import statistics
import argparse
from collections import Counter
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
    # antes del primer paquete del cliente puede haber basura del servidor
    # asi que hasta que no detectemos algo del cliente no empezamos a sumar
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
        if not participa:
            continue
        
        total_tls_bytes += sum(record_lengths)
        
        # dirección outgoing    
        if ip_src == client_ip:
            # feature A
            total_outgoing_records += total_records
            outgoing_sizes.extend(record_lengths)
            # feature E
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
            # feature E
            for r in record_lengths:
                if 1 <= r <= MAX_TLS_RECORD_SIZE:
                    incoming_freq[r - 1] += 1
                    
        # ahora para los features B1 y B2 --> solo para la conexión 443
        conexion = (
            (ip_src == client_ip and ip_dst == server_ip and dst_port == str(server_port)) or
            (ip_src == server_ip and ip_dst == client_ip and src_port == str(server_port))  
        )
        
        if conexion:
            # paquete del cliente --> cierra burst actual y empieza uno nuevo
            if ip_src == client_ip:
                if visto_cliente:
                    # feature B1
                    # bytes TLS por el servidor entre dos paquetes del cliente
                    burst_b1.append(burst_actual)
                burst_actual = 0
                visto_cliente = True
                # feature B2
                secuencia.append(('C', total_records))
            else:
                # paquete del servidor --> acumula bytes TLS en el burst actual
                if visto_cliente:
                    # feature B1
                    burst_actual += sum(record_lengths)
                # feature B2
                secuencia.append(('S', total_records))
                
    bloques_b2: list[int] = []  # para almacenar los bloques de 20 records del servidor en B2
    cont_s = 0  # contador de records del servidor en la secuencia
    bloque_cont = 0  # contador de records en el bloque actual
        
    for origen, n in secuencia:
        restante = n
        while restante > 0:
            espacio = BURST_BLOCK_SIZE - bloque_cont
            tomar = min(restante, espacio)
            
            if origen == 'S':
                cont_s += tomar
                    
            bloque_cont += tomar
            restante -= tomar
                
            if bloque_cont == BURST_BLOCK_SIZE:
                # bloque completo de 20 records del servidor
                bloques_b2.append(cont_s)
                bloque_cont = 0
                cont_s = 0
                    
    # con la función de antes --> top 20 tamaños menos frecuentes
        
    incomin_top20 = top20Sizes(incoming_sizes)
    outgoing_top20 = top20Sizes(outgoing_sizes)
        
    # obtenemos las estadísticas
        
    min_b1, max_b1, std_b1, mean_b1, median_b1 = burstStats(burst_b1)
    min_b2, max_b2, std_b2, mean_b2, median_b2 = burstStats(bloques_b2)
        
    num_incomingDiff = len(set(incoming_sizes))
    num_outgoingDiff = len(set(outgoing_sizes))
    
    # CUARTO PASO --> ensamblamos el vector del paper
    
    vector = []
    
    # a) ConnStats --> [0 ... 2]
    vector += [total_incoming_records, total_outgoing_records, total_tls_bytes]
    
    # b) b1_BurstStats --> [3 ... 7]   
    vector += [min_b1, max_b1, std_b1, mean_b1, median_b1]
    
    # b) b2_BurstStats --> [8 ... 12]
    vector += [min_b2, max_b2, std_b2, mean_b2, median_b2]  
    
    # c) num_incomingDiff y num_outgoingDiff --> [13 ... 14]
    vector += [num_incomingDiff, num_outgoingDiff]
    
    # d) 20 tamaños menos frecuentes incoming --> [15 ... 54]
    vector += incomin_top20
    vector += outgoing_top20
    
    # e) frecuencia de tamaños (todos los tamaños posibles)
    vector += incoming_freq
    vector += outgoing_freq
    
    assert len(vector) == 36_919, f"Error: vector tiene {len(vector)} features, esperados 36,919"
    
    return vector   

# ponemos etiquetas a las métricas extraídas a partir 
# del nombre del fichero --> realmente no sé todavía que ponerles jeje

def nombrarFichero(pcap_file: str) -> str:
    return os.path.splitext(os.path.basename(pcap_file))[0]
    # más adelante supongo que los nombres serán diferentes

# En caso del TFM --> hay que evaluar muchos pcaps de un solo escenario --> 
# hacemos que este código lea y calcule las métricas de todos los pcaps del escenario
# que están almacenados en sus respectivos ficheros y los guardamos en un directorio de
# resultados :)

def procesarDirectorio(
    directorio: str,
    client_ip: str,
    server_ip: str,
    server_port: int,
    output_path: str,
) -> None:
    
    pcaps = sorted([
        f for f in os.listdir(directorio) 
        if f.endswith(".pcap")
    ])
    
    if not pcaps:
        print(f"No se encontraron archivos .pcap en el directorio: {directorio}")
        return
    
    cabecera = ["label"] + [f"feature_{i}" for i in range(36919)]
    errores = []
    
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cabecera)
        
        for i, nombre in enumerate(pcaps):
            pcap_path = os.path.join(directorio, nombre)
            etiqueta = nombrarFichero(nombre)
            print(f"[{i+1}/{len(pcaps)}] {nombre}  →  label: '{etiqueta}'", end="", flush=True)
            try:
                vector = extraer_todas_las_features(
                    pcap_file=pcap_path,
                    client_ip=client_ip,
                    server_ip=server_ip,
                    server_port=server_port,
                )
                writer.writerow([etiqueta] + vector)
            except Exception as e:
                print(f"\nError procesando {nombre}: {e}")
                errores.append((nombre, str(e)))

    print(f"\nProcesamiento completado. Resultados guardados en: {output_path}")
    if errores:
        print(f"Ficheros con errores: {errores}")

if __name__ == "__main__":
    client_ip = "172.16.56.2"
    server_ip = "172.16.56.1"
    server_port = 443
    
    parser = argparse.ArgumentParser(
        description= "Extrae el vector de features H2Classifier de un archivo PCAP"
    )
    parser.add_argument(
        "directorio",
        help="Ruta al directorio que contiene los archivos .pcap"
    )
    parser.add_argument(
        "--output", "-o",
        default="datos/resultados/features.csv",
        help="Ruta al archivo CSV de salida"
    )
    args = parser.parse_args()
    
    if args.output:
        output_path = args.output
    else:
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(args.directorio, f"features_{timestamp}.csv")
    
    procesarDirectorio(
        directorio=args.directorio,
        client_ip=client_ip,
        server_ip=server_ip,
        server_port=server_port,
        output_path=output_path,
    )