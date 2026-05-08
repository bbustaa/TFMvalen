## Genera el mapeo {basename_pcap -> dominio_web} a partir del fichero txt
## de metadatos del escenario Open World.
## <pageNum> <ID> <URL> intento <attemptNum> <pcap_path> <sslkey_path>
## Uso directo:
##  python mapeo_pcaps_OW.py metadatos_OW.txt
##  python mapeo_pcaps_OW.py metadatos_OW.txt --output mapeo.json

import argparse
import json
import os
from urllib.parse import urlparse

def cargar_mapeo_pcaps(txt_path: str) -> dict[str, str]:

    mapeo: dict[str, str] = {}

    with open(txt_path, "r") as f:
        for num_linea, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue

            partes = linea.split()
            if len(partes) < 6:
                print(f"[línea {num_linea}] formato inesperado, se ignora: {linea!r}")
                continue

            url      = partes[2]   # https://bing.com
            pcap_abs = partes[5]   # /mnt/.../captura_0000040_11.pcap

            dominio  = _extraer_dominio(url)
            basename = os.path.basename(pcap_abs)

            mapeo[basename] = dominio

    return mapeo

def _extraer_dominio(url: str) -> str:

    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def cargar_dominios_monitorizados(fichero: str) -> set[str]:

    dominios: set[str] = set()
    with open(fichero, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            # si tiene esquema (http/https) lo tratamos como URL completa
            if "://" in linea:
                dominios.add(_extraer_dominio(linea))
            else:
                # ya es un dominio, quitamos www. si lo tiene
                netloc = linea.lstrip("www.") if linea.startswith("www.") else linea
                dominios.add(netloc)
    return dominios


def guardar_mapeo_json(mapeo: dict[str, str], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapeo, f, indent=2, ensure_ascii=False)
    print(f"Mapeo guardado en: {output_path}")


def imprimir_resumen(mapeo: dict[str, str]) -> None:
    dominios = set(mapeo.values())
    print(f"PCaps mapeados  : {len(mapeo)}")
    print(f"Dominios únicos : {len(dominios)}")
    print("\nDominios encontrados:")
    for d in sorted(dominios):
        count = sum(1 for v in mapeo.values() if v == d)
        print(f"  {d:<40} ({count} capturas)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera el mapeo pcap→dominio a partir del fichero txt de metadatos OW"
    )
    parser.add_argument(
        "txt",
        help="Ruta al fichero txt de metadatos OW"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Ruta donde guardar el mapeo en JSON (opcional)"
    )
    args = parser.parse_args()

    mapeo = cargar_mapeo_pcaps(args.txt)
    imprimir_resumen(mapeo)

    if args.output:
        guardar_mapeo_json(mapeo, args.output)
