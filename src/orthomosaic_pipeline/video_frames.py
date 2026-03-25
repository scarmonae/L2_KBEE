from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
from rich.console import Console
from tqdm import tqdm

console = Console()

_FORMAT_EXTENSIONS = {
    "png": ".png",
    "jpg": ".jpg",
    "jpeg": ".jpg",
}


def _normalize_image_format(image_format: str) -> str:
    fmt = image_format.strip().lower().lstrip(".")
    if fmt not in _FORMAT_EXTENSIONS:
        valid = ", ".join(sorted(_FORMAT_EXTENSIONS))
        raise ValueError(f"Formato de imagen no soportado: {image_format}. Usa: {valid}")
    return "jpg" if fmt == "jpeg" else fmt


def _validate_video_path(video_path: Path) -> Path:
    video_path = video_path.expanduser()
    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video: {video_path}")
    if not video_path.is_file():
        raise FileNotFoundError(f"La ruta no apunta a un archivo: {video_path}")
    return video_path


def _resolve_output_dir(video_path: Path, out_dir: Optional[Path], crop_top_px: int) -> Path:
    if out_dir is None:
        out_dir = video_path.with_name(f"{video_path.stem}_frames_top{crop_top_px}")

    out_dir = out_dir.expanduser()
    if out_dir.exists():
        if not out_dir.is_dir():
            raise NotADirectoryError(f"La ruta de salida no es un directorio: {out_dir}")
        if any(out_dir.iterdir()):
            raise FileExistsError(
                f"El directorio de salida ya existe y no esta vacio: {out_dir}"
            )
    else:
        out_dir.mkdir(parents=True, exist_ok=False)

    return out_dir


def _frame_number_width(frame_count: int) -> int:
    if frame_count <= 0:
        return 6
    return max(6, len(str(frame_count - 1)))


def _crop_frame(frame, crop_top_px: int):
    if crop_top_px == 0:
        return frame
    return frame[crop_top_px:, :, :]


def _save_frame(
    frame,
    frame_index: int,
    out_dir: Path,
    crop_top_px: int,
    image_format: str,
    number_width: int,
) -> Path:
    cropped = _crop_frame(frame, crop_top_px)
    frame_name = f"frame_{frame_index:0{number_width}d}{_FORMAT_EXTENSIONS[image_format]}"
    frame_path = out_dir / frame_name

    if image_format == "jpg":
        ok = cv2.imwrite(str(frame_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
    else:
        ok = cv2.imwrite(str(frame_path), cropped)

    if not ok:
        raise OSError(f"No se pudo guardar el frame en {frame_path}")

    return frame_path


def extract_video_frames(
    video_path: Path,
    out_dir: Optional[Path] = None,
    crop_top_px: int = 100,
    image_format: str = "png",
) -> Path:
    if crop_top_px < 0:
        raise ValueError("crop_top_px no puede ser negativo")

    video_path = _validate_video_path(video_path)
    image_format = _normalize_image_format(image_format)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, first_frame = capture.read()
        if not ok or first_frame is None:
            raise ValueError(f"No se pudo leer el primer frame de {video_path}")

        frame_height = int(first_frame.shape[0])
        if crop_top_px >= frame_height:
            raise ValueError(
                "crop_top_px debe ser menor que la altura del frame "
                f"({crop_top_px} >= {frame_height})"
            )

        out_dir = _resolve_output_dir(video_path, out_dir, crop_top_px)
        number_width = _frame_number_width(frame_count)

        saved_frames = 0
        with tqdm(
            total=frame_count if frame_count > 0 else None,
            desc="Extrayendo frames",
            unit="frame",
        ) as progress:
            _save_frame(first_frame, 0, out_dir, crop_top_px, image_format, number_width)
            saved_frames += 1
            progress.update(1)

            frame_index = 1
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                _save_frame(frame, frame_index, out_dir, crop_top_px, image_format, number_width)
                saved_frames += 1
                frame_index += 1
                progress.update(1)

        console.print(f"[green]Guardado[/green] {saved_frames} frames en {out_dir}")
        console.print(
            f"[cyan]Recorte aplicado:[/cyan] {crop_top_px}px superiores, formato {image_format}"
        )
        return out_dir
    finally:
        capture.release()
