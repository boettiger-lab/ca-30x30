from utils import *
import re

def convert_h3(con, s3, folder, file, cols, zoom, base_folder = "CBN/"):
    """
    Driver function to convert geometries to h3.
    If no zoom levels exist -> compute from geometry at target zoom.
    """
    cols = ", ".join(cols) if isinstance(cols, list) else cols
    bucket, path = info(folder, file, base_folder)
    path, file = os.path.split(path)
    name, ext = os.path.splitext(file)
    name = name.replace('-', '')
    print(f"Processing: {name}")

    hex_paths = s3.list_objects(bucket, prefix=f"{path}/hex/", recursive=True)
    zooms = []
    # check what zooms exist 
    for obj in hex_paths:
        match = re.search(r"/zoom(\d{1,2})/", obj.object_name)
        if match:
            zooms.append(int(match.group(1)))
            
    if not zooms: # if no h3 files exist
        print(f'No h3 files exists, computing zoom level {zoom} from geometry.')
        con.read_parquet(f"s3://{bucket}/{path}/{file}", table_name=name)
        h3_from_geom(con, name, cols, zoom)
        con.sql(f'''
            SELECT {cols}, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
        ''').to_parquet(f"s3://{bucket}/{path}/hex/zoom{zoom}/{name}.parquet")

    else: 
        current_zoom = max(zooms)            
        
        if zoom in zooms:
            print(f'Zoom {zoom} already exists!')
            return 
            
        # elif current_zoom < zoom: #compute child of most refined zoom level
        #     print(f'Reading zoom {current_zoom}')
        #     con.read_parquet(
        #         f"s3://{bucket}/{path}/hex/zoom{current_zoom}/{name}.parquet",
        #         table_name=f"h3_h{current_zoom}"
        #     )
        #     print(f'Computing {zoom} from {current_zoom}')
            
        #     for z in range(current_zoom + 1, zoom + 1):
        #         print(f'Current zoom {z}')
        #         h3_from_parent(con, z)
        #         con.sql(f'''
        #             SELECT *, UNNEST(h3_cell_to_children(h{z-1}, {z})) AS h{z}
        #             FROM h3_h{z-1}
        #         ''').to_parquet(f"s3://{bucket}/{path}/hex/zoom{z}/{name}.parquet")
  
    
def h3_from_geom(con, name, cols, zoom):
    """
    Computes hexes directly from geometry.
    """
    con.raw_sql(f'''
    CREATE OR REPLACE TEMP TABLE t2 AS
    SELECT {cols},
           h3_polygon_wkt_to_cells_string(ST_Force2D(dump.geom), {zoom}) AS h{zoom}
    FROM (
        SELECT {cols}, UNNEST(ST_Dump(geom)) AS dump
        FROM {name}
    )
    ''')


# def h3_from_parent(con, zoom):
#     con.raw_sql(f'''
#         CREATE OR REPLACE TEMP TABLE h3_h{zoom} AS
#         SELECT *, UNNEST(h3_cell_to_children(h{zoom-1}, {zoom})) AS h{zoom}
#         FROM h3_h{zoom-1}
#     ''')
