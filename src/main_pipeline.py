import os
import shutil
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import Point

from .config import Paths, SITES_WGS84, CRS_METRIC
from .io_loaders import load_grid_excel, load_constraints
from .grid_ops import build_grid_gdf
from .analysis_ops import calc_distance_bins, mask_constraints
from .viz_folium import build_map


def run_pipeline(paths: Paths):
    os.makedirs(paths.output_dir, exist_ok=True)
    os.makedirs(paths.docs_dir, exist_ok=True)

    # 1) 격자 엑셀 로드
    df = load_grid_excel(paths.excel_path)

    # 2) 격자 폴리곤 생성 (여기서 아직 NotImplementedError가 나는 게 정상)
    gdf_grid = build_grid_gdf(df, grid_col="격자코드")

    # 3) 불가용지 로드 + union
    constraints_gdf = load_constraints(paths.constraint_shps)
    constraints_union = unary_union(constraints_gdf.geometry) if len(constraints_gdf) else None

    for site_name, (lon, lat) in SITES_WGS84.items():
        site_pt_5179 = (
            gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
            .to_crs(CRS_METRIC)
            .iloc[0]
        )

        g = calc_distance_bins(gdf_grid, site_pt_5179)

        if constraints_union is not None:
            g = mask_constraints(g, constraints_union)
        else:
            g["is_masked"] = False

        out_html = os.path.join(paths.output_dir, f"map_{site_name}_final.html")
        build_map(g, site_name, (lon, lat), out_html)

        # GitHub Pages용 docs 폴더에 복사
        shutil.copy(out_html, os.path.join(paths.docs_dir, f"map_{site_name}.html"))

    # 4) docs/index.html 생성
    idx_path = os.path.join(paths.docs_dir, "index.html")
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n")
        f.write("<html lang='ko'>\n")
        f.write("<head><meta charset='utf-8'/><title>Seoul 100m Grid Maps</title></head>\n")
        f.write("<body>\n")
        f.write("<h2>Seoul 100m Grid Analysis</h2>\n")
        f.write("<ul>\n")
        f.write("<li><a href='./map_잠실야구장.html'>잠실야구장</a></li>\n")
        f.write("<li><a href='./map_상암월드컵경기장.html'>상암월드컵경기장</a></li>\n")
        f.write("<li><a href='./map_고척스카이돔.html'>고척스카이돔</a></li>\n")
        f.write("</ul>\n")
        f.write("</body></html>\n")
