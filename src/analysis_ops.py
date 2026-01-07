import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from .config import BIN_M, DIST_MAX_M

def calc_distance_bins(gdf: gpd.GeoDataFrame, site_point_5179: Point) -> gpd.GeoDataFrame:
    dx = gdf["cx"].to_numpy() - site_point_5179.x
    dy = gdf["cy"].to_numpy() - site_point_5179.y
    dist = np.sqrt(dx*dx + dy*dy)

    out = gdf.copy()
    out["dist_m"] = dist
    out = out[out["dist_m"] <= DIST_MAX_M].copy()

    out["bin_idx"] = (out["dist_m"] // BIN_M).astype(int)
    out["bin_label"] = (out["bin_idx"]*BIN_M).astype(int).astype(str) + "~" + ((out["bin_idx"]+1)*BIN_M).astype(int).astype(str)
    return out

def mask_constraints(gdf: gpd.GeoDataFrame, constraints_union) -> gpd.GeoDataFrame:
    out = gdf.copy()
    out["is_masked"] = out.geometry.intersects(constraints_union)
    return out
