import ibis
from ibis import _

conn = ibis.duckdb.connect("tmp3", extensions=["spatial"])
# ca_parquet = "https://data.source.coop/cboettig/ca30x30/ca_areas.parquet"
# or use local copy:
ca_parquet = "ca_areas.parquet"


# negative buffer to account for overlapping boundaries. 
buffer = -30 #30m buffer 

tbl = (
    conn.read_parquet(ca_parquet)
    .cast({"SHAPE": "geometry"})
    .rename(geom = "SHAPE")
    .filter(_.reGAP < 3) # only gap 1 and 2 count towards 30x30
)

# polygons with release_year 2024 are a superset of release_year 2023. 
# use anti_join to isolate the objects that are in release_year 2024 but not release_year 2023 (aka newly established). 
tbl_2023 = tbl.filter(_.Release_Year == 2023).mutate(geom=_.geom.buffer(buffer)) 
tbl_2024 = tbl.filter(_.Release_Year == 2024)
intersects = tbl_2024.anti_join(tbl_2023, _.geom.intersects(tbl_2023.geom))

new2024 = intersects.select("OBJECTID").mutate(established = 2024) # saving IDs to join on

ca = (conn
      .read_parquet(ca_parquet)
      .cast({"SHAPE": "geometry"})
      .mutate(area = _.SHAPE.area())
      .filter(_.Release_Year == 2024) # having both 2023 and 2024 is redudant since 2024 is the superset.
      .left_join(new2024, "OBJECTID") # newly established 2024 polygons 
      .mutate(established=_.established.fill_null(2023)) 
      .mutate(geom = _.SHAPE.convert("epsg:3310","epsg:4326"))
      .rename(name = "cpad_PARK_NAME", access_type = "cpad_ACCESS_TYP", manager = "cpad_MNG_AGENCY",
              manager_type = "cpad_MNG_AG_LEV", id = "OBJECTID", type = "TYPE")
      .mutate(manager = _.manager.substitute({"": "Unknown"})) 
      .mutate(manager_type = _.manager_type.substitute({"": "Unknown"}))
      .mutate(access_type = _.access_type.substitute({"": "Unknown Access"}))
      .mutate(name = _.name.substitute({"": "Unknown"}))
      .select(_.established, _.reGAP, _.name, _.access_type, _.manager, _.manager_type,
              _.Easement, _.Acres, _.id, _.type, _.geom)
     )

ca2024 = ca.execute()

ca2024.to_parquet("ca2024-30m.parquet")

ca2024.to_file("ca2024-30m.geojson") # tippecanoe can't parse geoparquet :-(


## Upload to Huggingface
# https://huggingface.co/datasets/boettiger-lab/ca-30x30/

from huggingface_hub import HfApi, login
import streamlit as st
login(st.secrets["HF_TOKEN"])
api = HfApi()

def hf_upload(file):
    info = api.upload_file(
            path_or_fileobj=file,
            path_in_repo=file,
            repo_id="boettiger-lab/ca-30x30",
            repo_type="dataset",
        )
hf_upload("ca2024-30m.parquet")



import subprocess
import os

def generate_pmtiles(input_file, output_file, max_zoom=12):
    # Ensure Tippecanoe is installed
    if subprocess.call(["which", "tippecanoe"], stdout=subprocess.DEVNULL) != 0:
        raise RuntimeError("Tippecanoe is not installed or not in PATH")

    # Construct the Tippecanoe command
    command = [
        "tippecanoe",
        "-o", output_file,
        "-z", str(max_zoom),
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--force",
        input_file
    ]

    # Run Tippecanoe
    try:
        subprocess.run(command, check=True)
        print(f"Successfully generated PMTiles file: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error running Tippecanoe: {e}")

generate_pmtiles("ca2024-30m.geojson", "ca2024-30m-tippe.pmtiles")
hf_upload("ca2024-30m-tippe.pmtiles")