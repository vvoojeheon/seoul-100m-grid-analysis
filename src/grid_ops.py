import re
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from pyproj import Transformer
from typing import Tuple

from .config import CRS_METRIC, SITES_WGS84

# (1) 격자코드 파싱: "다사629455" -> (i=629, j=455)
_GRID_RE = re.compile(r"^[가-힣]{2}(\d{6})$")

def _parse_ij(code: str) -> Tuple[int, int]:
    code = str(code).strip()
    m = _GRID_RE.match(code)
    if not m:
        raise ValueError(f"격자코드 형식 오류: {code}")
    n = int(m.group(1))
    i = n // 1000
    j = n % 1000
    return i, j

def _bin_to_range_m(s: str) -> Tuple[float, float]:
    # '2km~3km', '500m~1km', '0~500m', '1km~1.5km' 등
    s = str(s).strip()
    a, b = s.split("~")
    def to_m(x: str) -> float:
        x = x.strip()
        if x.endswith("km"):
            return float(x[:-2]) * 1000
        if x.endswith("m"):
            return float(x[:-1])
        return float(x)
    return to_m(a), to_m(b)

def _bin_mid_m(s: str) -> float:
    lo, hi = _bin_to_range_m(s)
    return 0.5 * (lo + hi)

def _sites_5179():
    t = Transformer.from_crs("EPSG:4326", CRS_METRIC, always_xy=True)
    out = {}
    for name, (lon, lat) in SITES_WGS84.items():
        out[name] = t.transform(lon, lat)
    return out

def _calibrate_decoder(df: pd.DataFrame, sample_n: int = 12000, random_state: int = 42):
    """
    목적: (i,j) -> (x,y) 변환을 '거리구간'과 최대한 일치하도록 추정.
    가정: 100m 격자이므로 (x,y)는 i/j에 대해 100m 단위 선형 + 상수 형태이며,
         x축/ y축에 i/j가 어떻게 매핑되는지(스왑)만 모를 수 있음.
    출력: (base_x, base_y, swap)
          swap=False: x=base_x + i*100 + 50, y=base_y + j*100 + 50
          swap=True : x=base_x + j*100 + 50, y=base_y + i*100 + 50
    """
    need_cols = {"대상지", "거리구간", "격자코드"}
    miss = need_cols - set(df.columns)
    if miss:
        raise ValueError(f"엑셀에 필수 컬럼이 없습니다: {miss}")

    sites5179 = _sites_5179()

    # 샘플링(속도)
    dfx = df[df["대상지"].isin(sites5179.keys())].copy()
    if len(dfx) == 0:
        raise ValueError("엑셀 '대상지' 값이 config의 SITES_WGS84 키와 일치하지 않습니다.")

    if len(dfx) > sample_n:
        dfx = dfx.sample(sample_n, random_state=random_state)

    # ij 벡터화 파싱
    codes = dfx["격자코드"].astype(str).to_numpy()
    ij = np.array([_parse_ij(c) for c in codes], dtype=float)
    I = ij[:, 0]
    J = ij[:, 1]

    # 목표 거리: 거리구간 중앙값
    target = np.array([_bin_mid_m(s) for s in dfx["거리구간"].astype(str).to_numpy()], dtype=float)

    # 사이트 좌표
    sx = np.array([sites5179[n][0] for n in dfx["대상지"].to_numpy()], dtype=float)
    sy = np.array([sites5179[n][1] for n in dfx["대상지"].to_numpy()], dtype=float)

    # swap 두 케이스 중 더 좋은 것을 선택 (base_x/base_y는 중심 근처로 추정)
    # base는 "사이트좌표 - 100m*index"의 중앙값으로 시작한 뒤, 간단한 랜덤 탐색으로 개선
    def eval_case(swap: bool, iters: int = 250):
        if not swap:
            px = I; py = J
        else:
            px = J; py = I

        # 초기 base (중앙값 기반)
        bx0 = np.median(sx - (px * 100 + 50))
        by0 = np.median(sy - (py * 100 + 50))

        def score(bx, by):
            cx = bx + (px * 100 + 50)
            cy = by + (py * 100 + 50)
            dist = np.sqrt((cx - sx) ** 2 + (cy - sy) ** 2)
            # 목표(거리구간 중앙값)와의 오차 (L1)
            return np.mean(np.abs(dist - target))

        best_bx, best_by = bx0, by0
        best_sc = score(bx0, by0)

        rng = np.random.default_rng(0)
        # 탐색 폭(미터): 처음 넓게, 점점 줄이기
        steps = np.linspace(5000, 200, iters)
        for st in steps:
            cand_bx = best_bx + rng.normal(0, st)
            cand_by = best_by + rng.normal(0, st)
            sc = score(cand_bx, cand_by)
            if sc < best_sc:
                best_sc = sc
                best_bx, best_by = cand_bx, cand_by

        return best_bx, best_by, best_sc

    bx1, by1, sc1 = eval_case(False)
    bx2, by2, sc2 = eval_case(True)

    if sc2 < sc1:
        return bx2, by2, True
    return bx1, by1, False

_DECODER = None  # (base_x, base_y, swap)

def build_grid_gdf(df: pd.DataFrame, grid_col: str = "격자코드") -> gpd.GeoDataFrame:
    global _DECODER
    if _DECODER is None:
        _DECODER = _calibrate_decoder(df)
        print(f"[decoder] base_x={_DECODER[0]:.3f}, base_y={_DECODER[1]:.3f}, swap={_DECODER[2]}")

    base_x, base_y, swap = _DECODER

    codes = df[grid_col].astype(str).to_numpy()
    ij = np.array([_parse_ij(c) for c in codes], dtype=float)
    I = ij[:, 0]
    J = ij[:, 1]

    if not swap:
        cx = base_x + (I * 100 + 50)
        cy = base_y + (J * 100 + 50)
    else:
        cx = base_x + (J * 100 + 50)
        cy = base_y + (I * 100 + 50)

    # 100m x 100m 폴리곤 (센터 기준)
    half = 50.0
    geoms = [box(x - half, y - half, x + half, y + half) for x, y in zip(cx, cy)]

    gdf = gpd.GeoDataFrame(df.copy(), geometry=geoms, crs=CRS_METRIC)
    gdf["cx"] = cx
    gdf["cy"] = cy
    return gdf
