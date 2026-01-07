import pandas as pd
import geopandas as gpd
from typing import List
from .config import CRS_METRIC

def load_grid_excel(excel_path: str) -> pd.DataFrame:
    df = pd.read_excel(excel_path)
    return df

def load_constraints(shp_paths: List[str]) -> gpd.GeoDataFrame:
    gdfs = []
    for p in shp_paths:
        g = gpd.read_file(p)
        if g.crs is None:
            g = g.set_crs(CRS_METRIC)
        else:
            g = g.to_crs(CRS_METRIC)
        gdfs.append(g)

    if len(gdfs) == 0:
        return gpd.GeoDataFrame(geometry=[], crs=CRS_METRIC)

    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=CRS_METRIC)
