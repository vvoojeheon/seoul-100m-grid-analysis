from .config import Paths
from .main_pipeline import run_pipeline

if __name__ == "__main__":
    paths = Paths(
        excel_path="Verified_Final_Data.xlsx",
        constraint_shps=[
            "data/constraints/LSMD_CONT_UD801_11_202512.shp",
            "data/constraints/LSMD_CONT_UI701_11_202512.shp",
            "data/constraints/LSMD_CONT_UM102_11_202512.shp",
            "data/constraints/LSMD_CONT_UM720_11_202512.shp",
            "data/constraints/LSMD_CONT_UM730_11_202512.shp",
        ],
        output_dir="outputs",
        docs_dir="docs",
    )
    run_pipeline(paths)
