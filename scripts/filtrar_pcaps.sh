#!/bin/bash

# ============================================================
# filtrar_pcaps.sh
# Copia los .pcap correspondientes a las URLs del listado final
# Uso: bash filtrar_pcaps.sh
# ============================================================

# --- RUTAS (ajusta si es necesario) ---
LISTADO="datos/open_world/urls/listado_final.txt"
DIR_PCAP="/RAID5-22TB/datos/v8x100/captura"           # carpeta donde están los .pcap
DIR_OUT="datos/open_world/pcaps_filtrados" # carpeta de destino

mkdir -p "$DIR_OUT"

# --- Extraer los IDs de URL del listado (primera columna) ---
# Ejemplo de línea: "1 https://google.com"  →  ID = 1
mapfile -t IDS < <(awk '{print $1}' "$LISTADO")

echo "URLs en el listado final: ${#IDS[@]}"
echo "Buscando pcaps en: $DIR_PCAP"
echo "Destino: $DIR_OUT"
echo "------------------------------------------------------------"

total_copiados=0
total_no_encontrados=0

for id in "${IDS[@]}"; do
    # Buscar por el sufijo final: captura_*_<id>.pcap
    # Ejemplo: id=94 → captura_*_94.pcap
    matches=( "$DIR_PCAP"/captura_*_${id}.pcap )

    if [ ${#matches[@]} -eq 0 ] || [ ! -f "${matches[0]}" ]; then
        echo "[NO ENCONTRADO] ID $id"
        ((total_no_encontrados++))
        continue
    fi

    for f in "${matches[@]}"; do
        cp "$f" "$DIR_OUT/"
        ((total_copiados++))
    done
    echo "[OK] ID $id → ${#matches[@]} pcap(s) copiados"
done

echo "------------------------------------------------------------"
echo "Total pcaps copiados   : $total_copiados"
echo "IDs sin pcaps          : $total_no_encontrados"
echo "Destino final          : $DIR_OUT"
