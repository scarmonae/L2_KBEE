from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Tuple

import pandas as pd
from rich.console import Console
from rich.table import Table

from .mrk_parser import parse_mrk_file

# Patrón para extraer el sufijo numérico de archivos tipo *_0003_D.JPG
IMAGE_RE = re.compile(r"_(\d{4})_D\.JPG$", re.IGNORECASE)
console = Console()


def _extract_photo_id(path: Path) -> Tuple[int, Path]:
    match = IMAGE_RE.search(path.name)
    if not match:
        raise ValueError(f"No se pudo obtener el identificador en {path.name}")
    return int(match.group(1)), path


def load_images(images_dir: Path) -> pd.DataFrame:
    """Escanea el directorio y devuelve photo_id + ruta para cada JPG."""
    rows = []
    for img_path in sorted(images_dir.glob("*.JPG")):
        try:
            photo_id, _ = _extract_photo_id(img_path)
            rows.append({"photo_id": photo_id, "image_name": img_path.name, "image_path": img_path})
        except ValueError:
            continue

    if not rows:
        raise FileNotFoundError(f"No se hallaron imágenes JPG en {images_dir}")

    return pd.DataFrame(rows)


def build_geotags(mrk_path: Path, images_dir: Path) -> pd.DataFrame:
    """
    Une metadata .MRK con las imágenes del directorio.
    """
    mrk_df = parse_mrk_file(mrk_path)
    imgs_df = load_images(images_dir)
    merged = imgs_df.merge(mrk_df, on="photo_id", how="left")

    missing = merged[merged["lat"].isna()]
    if not missing.empty:
        console.print(f"[red]Advertencia:[/red] {len(missing)} imágenes no tienen metadata MRK.")

    merged = merged.dropna(subset=["lat", "lon"]).sort_values("photo_id")
    return merged


def save_geotags_csv(df: pd.DataFrame, out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "image_name",
        "photo_id",
        "gps_time_s",
        "lat",
        "lon",
        "ellipsoid_h",
        "vel_n",
        "vel_e",
        "vel_v",
        "std_lat",
        "std_lon",
        "std_h",
        "quality_flag",
    ]
    df[cols].to_csv(out_csv, index=False)
    console.print(f"[green]Guardado[/green] geotags en {out_csv}")


def save_odm_geo(df: pd.DataFrame, out_geo: Path) -> None:
    """
    Exporta un geo.txt estilo ODM: image_name lat lon alt yaw pitch roll.
    Yaw/Pitch/Roll se dejan en cero por falta de orientación en .MRK.
    """
    out_geo.parent.mkdir(parents=True, exist_ok=True)
    with out_geo.open("w") as f:
        for _, row in df.iterrows():
            f.write(
                f"{row['image_name']} {row['lat']:.8f} {row['lon']:.8f} "
                f"{row['ellipsoid_h']:.3f} 0 0 0\n"
            )
    console.print(f"[green]Guardado[/green] geo.txt en {out_geo}")


def render_overview(df: pd.DataFrame) -> None:
    """Imprime un resumen rápido en consola."""
    table = Table(title="Geotags")
    table.add_column("Imgs", justify="right")
    table.add_column("Lat", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Alt (ellip)", justify="right")

    table.add_row(
        str(len(df)),
        f"{df['lat'].min():.6f}..{df['lat'].max():.6f}",
        f"{df['lon'].min():.6f}..{df['lon'].max():.6f}",
        f"{df['ellipsoid_h'].min():.2f}..{df['ellipsoid_h'].max():.2f}",
    )
    console.print(table)
