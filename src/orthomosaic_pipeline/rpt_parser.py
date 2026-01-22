from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_rpt(path: Path) -> Dict[str, Any]:
    """Carga el JSON .RPT y devuelve el nodo raíz."""
    data = json.loads(path.read_text())
    if "SURVEYING_REPORT_ROOT" in data:
        return data["SURVEYING_REPORT_ROOT"]
    return data


def summarize_rpt(path: Path) -> Dict[str, Any]:
    """Devuelve un resumen compacto de métricas útiles."""
    root = load_rpt(path)
    basic = root.get("BASIC_INFO_UNIT", {})
    cam = root.get("VISIBLE_CAM_INFO_UNIT", {})
    rtb = root.get("RTB_INFO_UNIT", {})

    return {
        "mission_id": basic.get("MISSION_ID"),
        "mission_start": basic.get("MISSION_START_TIME"),
        "fly_time_s": basic.get("FLY_TIME"),
        "total_captures": cam.get("TOTAL_CAP_NUM"),
        "rtk_fixed": cam.get("RTK_FIXED_NUM"),
        "rtk_float": cam.get("RTK_FLOAT_NUM"),
        "rtk_single": cam.get("RTK_SINGLE_NUM"),
        "rtk_other": cam.get("RTK_OTHER_NUM"),
        "rtk_trace": cam.get("RTK_DETAIL_INFO"),
        "rtb_loss_duration": rtb.get("RTB_LOSS_DURATION"),
    }

