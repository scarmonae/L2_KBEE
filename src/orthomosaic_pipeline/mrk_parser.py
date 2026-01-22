from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pandas as pd


NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def parse_mrk_line(line: str) -> Dict[str, float]:
    """
    Extrae los campos numéricos de una línea .MRK de DJI.

    Formato esperado (ejemplo):
    3 314615.773252 [2397] 456,N 149,E 373,V 6.15516672,Lat -75.44785637,Lon 2290.114,Ellh 1.248569, 1.376007, 2.862685 16,Q
    """
    numbers = NUMBER_RE.findall(line)
    if len(numbers) < 13:
        raise ValueError(f"Línea MRK inesperada: {line}")

    photo_id = int(numbers[0])
    gps_time_s = float(numbers[1])
    exposure = int(numbers[2])  # suele ser el índice de captura
    vel_n = float(numbers[3])
    vel_e = float(numbers[4])
    vel_v = float(numbers[5])
    lat = float(numbers[6])
    lon = float(numbers[7])
    ellipsoid_h = float(numbers[8])
    std_lat = float(numbers[9])
    std_lon = float(numbers[10])
    std_h = float(numbers[11])
    quality_flag = int(numbers[12])

    return {
        "photo_id": photo_id,
        "gps_time_s": gps_time_s,
        "exposure": exposure,
        "vel_n": vel_n,
        "vel_e": vel_e,
        "vel_v": vel_v,
        "lat": lat,
        "lon": lon,
        "ellipsoid_h": ellipsoid_h,
        "std_lat": std_lat,
        "std_lon": std_lon,
        "std_h": std_h,
        "quality_flag": quality_flag,
    }


def parse_mrk_file(mrk_path: Path) -> pd.DataFrame:
    """Carga todas las líneas del archivo .MRK en un DataFrame ordenado por photo_id."""
    rows: List[Dict[str, float]] = []
    for raw_line in mrk_path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            rows.append(parse_mrk_line(line))
        except ValueError:
            # dejamos trazas mínimas para debugging sin romper el flujo
            print(f"Omitiendo línea no parseable en {mrk_path.name!s}: {line}")

    if not rows:
        raise ValueError(f"No se pudieron extraer filas desde {mrk_path}")

    df = pd.DataFrame(rows).sort_values("photo_id").reset_index(drop=True)
    return df

