import folium
import geopandas as gpd
from folium.features import GeoJsonTooltip
from .config import CRS_WEB, GRADATION_BANDS_M, BIN_M, DIST_MAX_M

def _color_by_band(dist_m: float) -> str:
    if dist_m <= GRADATION_BANDS_M[0]: return "#2ca25f"
    if dist_m <= GRADATION_BANDS_M[1]: return "#99d8c9"
    if dist_m <= GRADATION_BANDS_M[2]: return "#fdd49e"
    return "#fc8d59"

def build_map(gdf_5179: gpd.GeoDataFrame, site_name: str, site_wgs84: tuple, out_html: str):
    gdf = gdf_5179.to_crs(CRS_WEB)

    m = folium.Map(location=[site_wgs84[1], site_wgs84[0]], zoom_start=12, control_scale=True)

    folium.Marker(
        location=[site_wgs84[1], site_wgs84[0]],
        popup=site_name,
        icon=folium.Icon(color="red", icon="info-sign"),
    ).add_to(m)

    # 1/3/5/10km 반경 원
    for r in [1000, 3000, 5000, 10000]:
        folium.Circle(location=[site_wgs84[1], site_wgs84[0]], radius=r, weight=2, fill=False).add_to(m)

    # 500m 구간별 토글 레이어
    n_bins = int(DIST_MAX_M // BIN_M)
    for idx in range(n_bins):
        layer = folium.FeatureGroup(name=f"{idx*BIN_M}~{(idx+1)*BIN_M}m", show=(idx < 2))
        sub = gdf[gdf["bin_idx"] == idx]

        def style_fn(feat):
            dist = feat["properties"]["dist_m"]
            if feat["properties"].get("is_masked", False):
                return {"color": "#555555", "weight": 0.5, "fillColor": "#555555", "fillOpacity": 0.12}
            base = _color_by_band(dist)
            return {"color": base, "weight": 0.7, "fillColor": base, "fillOpacity": 0.35}

        tooltip = GeoJsonTooltip(
            fields=["격자코드", "dist_m", "bin_label", "is_masked"],
            aliases=["격자코드", "거리(m)", "500m구간", "마스킹여부"],
            localize=True,
            sticky=False,
        )

        if len(sub):
            folium.GeoJson(
                data=sub.to_json(),
                style_function=style_fn,
                tooltip=tooltip,
                highlight_function=lambda x: {"weight": 2},
                name="grid",
            ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(out_html)
    return out_html
