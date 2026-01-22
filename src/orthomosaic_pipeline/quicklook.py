from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.transform import Affine
from rich.console import Console
from tqdm import tqdm

console = Console()


def _utm_crs(latitudes: np.ndarray, longitudes: np.ndarray) -> CRS:
    lon_mean = float(np.mean(longitudes))
    lat_mean = float(np.mean(latitudes))
    zone = int((lon_mean + 180) / 6) + 1
    epsg = (32600 if lat_mean >= 0 else 32700) + zone
    return CRS.from_epsg(epsg)


def _ensure_image_paths(df: pd.DataFrame, images_dir: Path) -> pd.DataFrame:
    if "image_path" in df.columns:
        return df
    df = df.copy()
    df["image_path"] = df["image_name"].apply(lambda n: images_dir / n)
    return df


def quicklook_mosaic(
    geotags: pd.DataFrame,
    images_dir: Path,
    out_path: Path,
    mosaic_gsd: float = 0.25,
    image_gsd: Optional[float] = None,
    max_size_px: int = 12000,
    max_image_px: Optional[int] = 2000,
) -> Path:
    """
    Genera un ortomosaico rápido (aproximado) suponiendo cámara nadir.
    - mosaic_gsd: resolución objetivo (metros/píxel) del lienzo final.
    - image_gsd: resolución estimada de las imágenes (si None -> mosaic_gsd).
    - max_size_px: tamaño máximo por lado para evitar consumir demasiada RAM.
    - max_image_px: redimensiona cada imagen si su lado mayor supera este valor.
    """
    geotags = _ensure_image_paths(geotags, images_dir)
    crs = _utm_crs(geotags["lat"].to_numpy(), geotags["lon"].to_numpy())
    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)

    xs, ys = transformer.transform(geotags["lon"].to_numpy(), geotags["lat"].to_numpy())
    geotags = geotags.assign(x_m=xs, y_m=ys)

    min_x, max_x = float(np.min(xs)), float(np.max(xs))
    min_y, max_y = float(np.min(ys)), float(np.max(ys))

    width = ceil((max_x - min_x) / mosaic_gsd) + 1
    height = ceil((max_y - min_y) / mosaic_gsd) + 1

    if width > max_size_px or height > max_size_px:
        raise ValueError(
            f"El lienzo ({width}x{height}) supera el límite {max_size_px}px. "
            "Usa un mosaic_gsd más grande."
        )

    canvas_sum = np.zeros((height, width, 3), dtype=np.float32)
    canvas_count = np.zeros((height, width, 1), dtype=np.float32)
    img_gsd = image_gsd or mosaic_gsd

    for _, row in tqdm(geotags.iterrows(), total=len(geotags), desc="Pintando imágenes"):
        img_path = Path(row["image_path"])
        img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img is None:
            console.print(f"[yellow]Aviso:[/yellow] no pude leer {img_path}")
            continue

        h_px, w_px, _ = img.shape
        if max_image_px and max(h_px, w_px) > max_image_px:
            scale = max_image_px / max(h_px, w_px)
            img = cv2.resize(
                img,
                (int(round(w_px * scale)), int(round(h_px * scale))),
                interpolation=cv2.INTER_AREA,
            )
            h_px, w_px, _ = img.shape
            effective_gsd = img_gsd / scale
        else:
            effective_gsd = img_gsd

        footprint_w_m = w_px * effective_gsd
        footprint_h_m = h_px * effective_gsd

        target_w = max(1, int(round(footprint_w_m / mosaic_gsd)))
        target_h = max(1, int(round(footprint_h_m / mosaic_gsd)))
        if target_w <= 1 or target_h <= 1:
            console.print(f"[yellow]Aviso:[/yellow] footprint muy pequeño para {img_path.name}, se omite.")
            continue

        resized = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)

        cx = int(round((row["x_m"] - min_x) / mosaic_gsd))
        cy = int(round((max_y - row["y_m"]) / mosaic_gsd))
        x0 = cx - target_w // 2
        y0 = cy - target_h // 2
        x1 = x0 + target_w
        y1 = y0 + target_h

        # Recortes a los límites del lienzo
        x0_clip, y0_clip = max(x0, 0), max(y0, 0)
        x1_clip, y1_clip = min(x1, width), min(y1, height)
        if x0_clip >= x1_clip or y0_clip >= y1_clip:
            continue

        dx0, dy0 = x0_clip - x0, y0_clip - y0
        dx1, dy1 = target_w - (x1 - x1_clip), target_h - (y1 - y1_clip)

        patch = resized[dy0:dy1, dx0:dx1]
        canvas_sum[y0_clip:y1_clip, x0_clip:x1_clip] += patch[:, :, ::-1]  # BGR -> RGB
        canvas_count[y0_clip:y1_clip, x0_clip:x1_clip] += 1

    mosaic = canvas_sum / np.maximum(canvas_count, 1)
    mosaic = mosaic.astype(np.uint8)

    transform = Affine(mosaic_gsd, 0, min_x, 0, -mosaic_gsd, max_y)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=mosaic.shape[0],
        width=mosaic.shape[1],
        count=3,
        dtype=mosaic.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        for i in range(3):
            dst.write(mosaic[:, :, i], i + 1)

    console.print(f"[green]Ortomosaico rápido guardado:[/green] {out_path}")
    return out_path
