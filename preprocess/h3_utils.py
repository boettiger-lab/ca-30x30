from utils import *

default_zoom = "8"
max_h3_n = 1_000_000   # if est total H3 cells > this -> process in chunks
chunk_n = 10_000     # chunk size (# of geoms)
big_n = 10_000        # if geoms > big_n -> they are "big" and processed individually 
batch_n = 5_000      # big geoms processed in batches of this size

def compute_h3(con, name, cols, zoom):
    """
    Computes hexes    
    """
    con.raw_sql(f'''
        CREATE OR REPLACE TEMP TABLE t2 AS
        WITH t1 AS (
            SELECT {cols}, ST_Dump(geom) AS geom 
            FROM {name}
        )
        SELECT {cols},
               h3_polygon_wkt_to_cells_string(UNNEST(geom).geom, {zoom}) AS h{zoom}
        FROM t1
    ''')
    
def check_size(con, name, zoom, sample_size):
    """
    Estimating size of geoms to decide if we need to process in chunks 
    """
    query = f"""
        SELECT 
            avg(len(h3_polygon_wkt_to_cells_string(ST_AsText(geom), {zoom}))::DOUBLE) AS avg_h3_len,
            max(len(h3_polygon_wkt_to_cells_string(ST_AsText(geom), {zoom}))) AS max_h3_len,
            count(*) AS total_rows
        FROM {name}
        USING SAMPLE {sample_size}
    """
    stats = con.sql(query).execute()
    avg_len = stats.iloc[0]['avg_h3_len']
    max_len = stats.iloc[0]['max_h3_len']
    total_rows = con.table(name).count().execute()

    est_total_h3 = avg_len * total_rows

    print(f"Estimated total H3 cells: {est_total_h3:,.0f}")
    print(f"Max H3 cells in one geometry: {max_len:,}")

    return est_total_h3, max_len

def chunk_large_geom(con, s3, bucket, path, name, zoom, big_n, batch_limit):
    """
    Individually processing large geoms (different from processing "chunks")
    """
    offset = 0
    i = 0
    while True:
        relative_key = f"{path}/hex/zoom{zoom}/{name}_large_{i:03d}.parquet"
        print(f"🟠 Checking large geometry batch {i} → {relative_key}")

        if exists_on_s3(s3, folder="", file=relative_key):  # we pass relative_key as `file`
            print(f"⏩ Skipping existing large batch: {relative_key}")
            offset += batch_limit
            i += 1
            continue

        print(f"📝 Writing large geometry batch {i} → {relative_key}")
        q = con.sql(f'''
            SELECT *, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
            WHERE len(h{zoom}) > {big_n}
            LIMIT {batch_limit} OFFSET {offset}
        ''')

        q.to_parquet(f"s3://{bucket}/{relative_key}")

        if q.count().execute() == 0:
            break

        offset += batch_limit
        i += 1

    return i

def join_large_geoms(con, s3, bucket, path, name, zoom):
    """
    If we had to process large geoms individually, join those datasets after conversion.
    """
    # check if any large files exist before trying to join
    test_key = f"{path}/hex/zoom{zoom}/{name}_large_000.parquet"

    if not exists_on_s3(s3, folder="", file=test_key):
        print("✅ No large geometry chunks to join.")
        return

    # join if it exists 
    con.raw_sql(f'''
        COPY (
            SELECT * FROM read_parquet('s3://{bucket}/{path}/hex/zoom{zoom}/{name}_large_*.parquet')
        )
        TO 's3://{bucket}/{path}/hex/zoom{zoom}/{name}_large.parquet'
        (FORMAT PARQUET)
    ''')
    

def chunk_geom(con, s3, bucket, path, name, zoom, limit, batch_limit, big_n):
    """
    Processing files in chunks. 
    """
    offset = 0
    i = 0
    
    while True:
        chunk_path = f"{path}/hex/zoom{zoom}/{name}_chunk{i:03d}.parquet"
        
        if exists_on_s3(s3, folder="", file=chunk_path):  # relative path passed as file
            print(f"⏩ Skipping existing chunk: {chunk_path}")
            offset += limit
            i += 1
            continue

        print(f"📝 Writing chunk {i} → {chunk_path}")
        q = con.sql(f'''
            SELECT *, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
            WHERE len(h{zoom}) <= {big_n}
            LIMIT {limit} OFFSET {offset}
        ''')
        q.to_parquet(f"s3://{bucket}/{chunk_path}")
        if q.count().execute() == 0:
            break
        offset += limit
        i += 1

    # process large geometries using same threshold and limit
    chunk_large_geom(con, s3, bucket, path, name, zoom, big_n, batch_limit)
    join_large_geoms(con, s3, bucket, path, name, zoom)
    return i



def join_chunked(con, bucket, path, name, zoom):
    """
    If we had to chunk the data, join those datasets after conversion.
    """
    con.raw_sql(f'''
        COPY (
        SELECT * FROM read_parquet('s3://{bucket}/{path}/hex/zoom{zoom}/{name}_chunk*.parquet')
        )
        TO 's3://{bucket}/{path}/hex/zoom{zoom}/{name}.parquet'
        (FORMAT PARQUET)
        ''')

def convert_h3(con, s3, folder, file, cols, zoom=default_zoom, limit=chunk_n, batch_limit = batch_n, big_n=big_n, max_h3_n = max_h3_n):
    """
    Driver function to convert geometries to h3
    """
    cols = ", ".join(cols) if isinstance(cols, list) else cols
    bucket, path = info(folder, file)
    path, file = os.path.split(path)
    name, ext = os.path.splitext(file)
    name = name.replace('-', '')

    print(f"Processing: {name}")
    con.read_parquet(f"s3://{bucket}/{path}/{file}", table_name=name)

    # Decide to chunk or not
    est_total, max_per_geom = check_size(con, name, zoom, sample_size=100)
    if est_total > max_h3_n or max_per_geom > big_n:
        print("Chunking due to estimated size")
        compute_h3(con, name, cols, zoom)
        chunk_geom(con, s3, bucket, path, name, zoom, limit, batch_limit, big_n)
        join_chunked(con, bucket, path, name, zoom)
    else:
        print("Writing single output")
        compute_h3(con, name, cols, zoom)
        con.sql(f'''
            SELECT *, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
        ''').to_parquet(f"s3://{bucket}/{path}/hex/zoom{zoom}/{name}.parquet")
