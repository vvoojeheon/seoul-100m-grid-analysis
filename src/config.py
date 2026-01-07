from dataclasses import dataclass
from typing import Dict, Tuple, List

CRS_METRIC = "EPSG:5179"
CRS_WEB = "EPSG:4326"

DIST_MAX_M = 10_000
BIN_M = 500
GRADATION_BANDS_M = [1000, 3000, 5000, 10000]

# 엑셀 '대상지' 값과 반드시 동일해야 함
SITES_WGS84: Dict[str, Tuple[float, float]] = {
    "잠실야구장": (127.0719, 37.5123),
    "상암월드컵": (126.8972, 37.5683),
    "고척돔": (126.8671, 37.4982),
}

@dataclass(frozen=True)
class Paths:
    excel_path: str
    constraint_shps: List[str]
    output_dir: str = "outputs"
    docs_dir: str = "docs"
