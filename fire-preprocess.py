
## Sidebar, prepare fire data
import requests
import zipfile
import geopandas as gpd

zip = "https://34c031f8-c9fd-4018-8c5a-4159cdff6b0d-cdn-endpoint.azureedge.net/-/media/calfire-website/what-we-do/fire-resource-assessment-program---frap/gis-data/april-2023/fire23-1gdb.zip'?rev=852b1296fecc483380284f7aad868659"

open("ca_fire2023.zip", 'wb').write(requests.get(zip).content)
with zipfile.ZipFile('ca_fire2023.zip', 'r') as zip_ref:
    zip_ref.extractall()

gdf = gpd.read_file("fire23_1.gdb", layer = "firep23_1")
gdf["geometry"] = gdf.geometry.make_valid()
gdf.to_parquet("fire23.parquet")

gdf = gpd.read_file("fire23_1.gdb", layer = "rxburn23_1")
gdf["geometry"] = gdf.geometry.make_valid()
gdf.to_parquet("rxburn23.parquet")

epsg = gdf.crs.to_string()


import ibis
from ibis import _
import sys
sys.path.append("../cng-python/")
from utils import set_secrets

con = ibis.duckdb.connect(extensions=["spatial"])
set_secrets(con) # configure s3 access

# ibis 'to_parquet' seems in ibis seems to assume epsg:4326, so let's convert to that first...
(con
  .read_parquet("fire23.parquet")
  .mutate(geometry = _.geometry.convert(epsg, "EPSG:4326"))
  .to_parquet("s3://public-fire/calfire-2023.parquet")
)

(con
  .read_parquet("rxburn23.parquet")
  .mutate(geometry = _.geometry.convert(epsg, "EPSG:4326"))
  .to_parquet("s3://public-fire/calfire-rxburn-2023.parquet")
)
