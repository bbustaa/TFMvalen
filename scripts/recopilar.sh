#!/bin/bash

set -euo pipefail

ORIGEN="/RAID5-22TB/datos/escenario1/captura"
DESTINO="/RAID5-22TB/valentina.bustamante/TFMvalen/datos/prueba1/escenario1/dataset"
LIMITE="captura_02100_2100.pcap"

mkdir -p "$DESTINO"

for archivo in "$ORIGEN"/captura_*.pcap; do
    nombre=$(basename "$archivo")

    if [[ "$nombre" > "$LIMITE" ]]; then
        continue
    fi

    cp "$archivo" "$DESTINO/"
    echo "Copiado: $nombre"
done

echo "Proceso completado."
