from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich.console import Console

from .geotags import build_geotags, render_overview, save_geotags_csv, save_odm_geo
from .quicklook import quicklook_mosaic
from .rpt_parser import summarize_rpt

app = typer.Typer(help="Pipeline mínima para geotags y ortomosaico rápido.")
console = Console()


@app.command("geotags")
def geotags_cmd(
    mrk_path: Path = typer.Argument(..., help="Ruta al archivo .MRK"),
    images_dir: Path = typer.Argument(..., help="Directorio con las imágenes JPG"),
    out_csv: Path = typer.Option(
        Path("output/dji_matrice_350_rtk/image_geotags.csv"),
        help="Archivo CSV de salida",
    ),
    odm_geo: Optional[Path] = typer.Option(
        None, help="Ruta opcional a geo.txt estilo OpenDroneMap"
    ),
) -> None:
    df = build_geotags(mrk_path, images_dir)
    save_geotags_csv(df, out_csv)
    if odm_geo:
        save_odm_geo(df, odm_geo)
    render_overview(df)


@app.command("rpt-summary")
def rpt_summary_cmd(
    rpt_path: Path = typer.Argument(..., help="Ruta al archivo .RPT"),
    out_json: Optional[Path] = typer.Option(None, help="Ruta de salida JSON (opcional)"),
) -> None:
    summary = summarize_rpt(rpt_path)
    console.print_json(data=summary)
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(summary, indent=2))
        console.print(f"[green]Guardado[/green] resumen en {out_json}")


@app.command("quicklook")
def quicklook_cmd(
    geotags_csv: Path = typer.Argument(..., help="CSV generado por 'geotags'"),
    images_dir: Path = typer.Argument(..., help="Directorio con las imágenes JPG"),
    out_path: Path = typer.Option(
        Path("output/dji_matrice_350_rtk/quicklook_orthomosaic.tif"),
        help="Ruta del GeoTIFF resultante",
    ),
    mosaic_gsd: float = typer.Option(
        0.25, help="Resolución del mosaico (m/píxel) – aumenta para reducir tamaño"
    ),
    image_gsd: Optional[float] = typer.Option(
        None,
        help="GSD estimada de las fotos (m/píxel). Si se omite se usa mosaic_gsd.",
    ),
    max_size_px: int = typer.Option(
        12000, help="Tamaño máximo por lado del lienzo para evitar agotar RAM"
    ),
    max_image_px: int = typer.Option(
        2000, help="Redimensionar imágenes si su lado mayor supera este valor (px)"
    ),
) -> None:
    df = pd.read_csv(geotags_csv)
    quicklook_mosaic(df, images_dir, out_path, mosaic_gsd, image_gsd, max_size_px, max_image_px)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
