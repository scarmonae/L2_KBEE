Pipeline para ortomosaicos con DJI Matrice 350 RTK + L2
=======================================================

Descripción rápida
------------------
- Se preparó un repositorio mínimo en Python para leer los archivos .MRK/.RPT del vuelo, generar geotags por imagen y producir un ortomosaico aproximado (quicklook) en GeoTIFF.
- El directorio de datos analizado: `data/01_RAW_L2/01_RAW_L2/DJI_202512170953_006_KBee` con 40 imágenes JPG numeradas `_0003` a `_0042`.
- Los geotags y salidas generadas quedan en `output/dji_matrice_350_rtk/`.

Estructura del proyecto
-----------------------
- `src/orthomosaic_pipeline/mrk_parser.py`: parser de líneas .MRK a DataFrame.
- `src/orthomosaic_pipeline/geotags.py`: empareja imágenes con MRK, exporta CSV y `geo.txt` (estilo OpenDroneMap).
- `src/orthomosaic_pipeline/rpt_parser.py`: lectura/resumen del .RPT de la misión.
- `src/orthomosaic_pipeline/quicklook.py`: generación de ortomosaico rápido (asume cámara nadir y orientación neutra).
- `src/orthomosaic_pipeline/cli.py`: CLI con comandos `geotags`, `rpt-summary`, `quicklook`.
- `output/dji_matrice_350_rtk/`: salidas generadas (CSV, geo.txt, GeoTIFF quicklook, resumen RPT).

Instalación
-----------
1) Crear venv (recomendado): `python3 -m venv .venv && source .venv/bin/activate`. Si `venv` no está disponible, se puede instalar dependencias con `python3 -m pip install --break-system-packages -r requirements.txt`.
2) Instalar requerimientos: `pip install -r requirements.txt`.
3) Exportar PYTHONPATH al ejecutar: `export PYTHONPATH=src`.

Datos revisados
---------------
- MRK (`DJI_202512170953_006_KBee_Timestamp.MRK`): 40 registros (IDs 3–42) con lat/lon, altura elipsoidal (~2290–2293 m), velocidades N/E/V y `quality_flag=16` (RTK single).
- RPT (`DJI_20251217102128_0001_D.RPT`): 40 capturas, 315 s de vuelo, todos los disparos con RTK single (sin soluciones fixed/float). Resumen exportado en `output/dji_matrice_350_rtk/rpt_summary.json`.
- Imágenes: 40 archivos JPG `DJI_..._####_D.JPG` en la misma carpeta.

Uso de la CLI
-------------
Asumiendo `PYTHONPATH=src` y trabajando desde la raíz del repo:

1) Geotags CSV + geo.txt (para ODM):
```
python3 -m orthomosaic_pipeline.cli geotags \
  data/01_RAW_L2/01_RAW_L2/DJI_202512170953_006_KBee/DJI_202512170953_006_KBee_Timestamp.MRK \
  data/01_RAW_L2/01_RAW_L2/DJI_202512170953_006_KBee \
  --odm-geo output/dji_matrice_350_rtk/geo.txt
```
Salida: `output/dji_matrice_350_rtk/image_geotags.csv` y `geo.txt` (yaw/pitch/roll en cero por falta de orientación en MRK).

2) Resumen de la misión (.RPT):
```
python3 -m orthomosaic_pipeline.cli rpt-summary \
  data/01_RAW_L2/01_RAW_L2/DJI_202512170953_006_KBee/DJI_20251217102128_0001_D.RPT \
  --out-json output/dji_matrice_350_rtk/rpt_summary.json
```

3) Ortomosaico rápido (quicklook, GeoTIFF):
```
python3 -m orthomosaic_pipeline.cli quicklook \
  output/dji_matrice_350_rtk/image_geotags.csv \
  data/01_RAW_L2/01_RAW_L2/DJI_202512170953_006_KBee \
  --mosaic-gsd 0.30 \
  --image-gsd 0.05 \
  --max-image-px 1200
```
Salida: `output/dji_matrice_350_rtk/quicklook_orthomosaic.tif` (CRS UTM zona 18N). El quicklook asume cámara nadir y no aplica orientación; es solo para inspección visual rápida.

Parámetros esenciales para un ortomosaico robusto
-------------------------------------------------
- Calibración de cámara: distancia focal, tamaño de píxel/sensor, centro principal, distorsión radial/tangencial.
- Orientación exterior por captura: lat/lon/altura, yaw/pitch/roll (o cuaterniones); precisión/STD de GNSS/IMU.
- Modelo del terreno: DEM/DSM de apoyo o altura de vuelo sobre terreno para ortorrectificación.
- Cobertura: traslape frontal/lateral suficiente y fotos sin desenfoque.
- Control: GCPs u observaciones PPK/RTK de alta calidad; parámetros de geodésica/CRS destino.
- Procesado: estrategia de ajuste por haces (bundle adjustment), filtrado de puntos/Tie points, seamlines y balance radiométrico antes del mosaico final.

Librerías y stacks Python relevantes (hallazgos web)
----------------------------------------------------
- **PyODM/NodeODM (OpenDroneMap)**: SDK Python para enviar trabajos a un nodo ODM (genera ortofotos, nubes, DEM). Docs: opendronemap.org/pyodm.
- **OpenSfM (Mapillary)**: pipeline SfM en Python/C++ para orientación y densificación; sirve como base fotogramétrica open-source.
- **uavgeo**: librería Python sobre xarray/geopandas para procesar mosaicos UAV (ejemplos de ortomosaico y análisis).
- **Agisoft Metashape Python API** (comercial): API completa para fotogrametría/ortofotos; scripts comunitarios disponibles.
- Complementos de soporte: `rasterio`, `opencv`, `pyproj`, `pandas`, `Pillow` para reproyección, lectura de EXIF y manipulación de imágenes.

Archivos generados (este corrido)
---------------------------------
- `output/dji_matrice_350_rtk/image_geotags.csv`: geotags por imagen (IDs 3–42).
- `output/dji_matrice_350_rtk/geo.txt`: formato ODM (lat/lon/alt, yaw/pitch/roll = 0).
- `output/dji_matrice_350_rtk/quicklook_orthomosaic.tif`: ortomosaico rápido (UTM 18N, gsd 0.30 m/px, imágenes reescaladas a 1200 px máx).
- `output/dji_matrice_350_rtk/rpt_summary.json`: resumen de misión.

Limitaciones y siguientes pasos
-------------------------------
- El quicklook usa solo geotags y asume orientación neutra; para ortomosaico métrico se recomienda procesar con OpenDroneMap (geo.txt ya listo) o un motor fotogramétrico completo con cámara calibrada.
- La altura elipsoidal (~2290 m) proviene del MRK; no se corrige a ortométrica. Ajustar si se dispone de geoid/DEM.
- Las imágenes empiezan en `_0003`; si hay más capturas en otra carpeta, repetir el flujo.
- Sugerido: integrar PyODM para lanzar un job a NodeODM, añadir lectura de yaw/pitch/roll si aparece en otros logs (IMU/LDR), y definir un CRS/DEM de destino para entrega final.
