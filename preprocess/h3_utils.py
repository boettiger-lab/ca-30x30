
def geom_to_h3(con, name, cols, zoom):
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
    
def check_size(con, name, zoom, sample_size=100):
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


def write_large_geoms(con, s3, bucket, path, name, zoom="8", geom_len_threshold=10_000):
    """
    Individually processing large geoms (different from processing "chunks")
    """
    offset = 0
    i = 0
    limit=3000
    while True:
        large_key = f"{path}/hex/{name}_large_{i:03d}.parquet"
        print(f"🟠 Checking large geometry batch {i} → {large_key}")

        #  check if file already exists in minio
        try:
            s3.stat_object(bucket, large_key)
            print(f"⏩ Skipping existing large batch: {large_key}")
            offset += limit
            i += 1
            continue
        except S3Error as err:
            if err.code != "NoSuchKey":
                raise  

        print(f"📝 Writing large geometry batch {i} → {large_key}")
        q = con.sql(f'''
            SELECT *, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
            WHERE len(h{zoom}) > {geom_len_threshold}
            LIMIT {limit} OFFSET {offset}
        ''')

        q.to_parquet(f"s3://{bucket}/{large_key}")

        if q.count().execute() == 0:
            break

        offset += limit
        i += 1

    return i

    
def join_large_geoms(con, s3, bucket, path, name):
    """
    If we had to process large geoms individually, join those datasets after conversion.
    """
    # check if any large files exist before trying to join
    test_key = f"{path}/hex/{name}_large_000.parquet"

    try:
        s3.stat_object(bucket, test_key)
    except S3Error as err:
        if err.code == "NoSuchKey":
            print("✅ No large geometry chunks to join.")
            return
        else:
            raise
    # join if it exists 
    con.raw_sql(f'''
        COPY (
            SELECT * FROM read_parquet('s3://{bucket}/{path}/hex/{name}_large_*.parquet')
        )
        TO 's3://{bucket}/{path}/hex/{name}_large.parquet'
        (FORMAT PARQUET)
    ''')


def chunk_data(con, s3, bucket, path, name, zoom="8", limit=100_000, geom_len_threshold=10_000):
    """
    Processing large files in chunks. 
    """
    offset = 0
    i = 0

    while True:
        chunk_path = f"{path}/hex/{name}_chunk{i:03d}.parquet"
        
        try:
            s3.stat_object(bucket, chunk_path)
            print(f"⏩ Skipping existing chunk: {chunk_path}")
            offset += limit
            i += 1
            continue
        except S3Error as err:
            if err.code != "NoSuchKey":
                raise

        print(f"📝 Writing chunk {i} → {chunk_path}")
        q = con.sql(f'''
            SELECT *, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
            WHERE len(h{zoom}) <= {geom_len_threshold}
            LIMIT {limit} OFFSET {offset}
        ''')
        q.to_parquet(f"s3://{bucket}/{chunk_path}")
        if q.count().execute() == 0:
            break
        offset += limit
        i += 1

    # process large geometries using same threshold and limit
    write_large_geoms(con, s3, bucket, path, name, zoom, geom_len_threshold=geom_len_threshold)
    join_large_geoms(con, s3, bucket, path, name)
    return i



def join_chunked(bucket, path, name):
    """
    If we had to chunk the data, join those datasets after conversion.
    """
    con.raw_sql(f'''
        COPY (
        SELECT * FROM read_parquet('s3://{bucket}/{path}/hex/{name}_chunk*.parquet')
        )
        TO 's3://{bucket}/{path}/hex/{name}.parquet'
        (FORMAT PARQUET)
        ''')

# def convert_h3(con, folder, file, cols, zoom="8", limit=100_000, geom_len_threshold=10_000):
def convert_h3(con, s3, folder, file, cols, zoom="8", limit=100_000, geom_len_threshold=5_000):
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
    est_total, max_per_geom = check_size(con, name, zoom)
    # if est_total > 500_000 or max_per_geom > geom_len_threshold:

    if est_total > 1_000_000 or max_per_geom > geom_len_threshold:
        print("Chunking due to estimated size")
        geom_to_h3(con, name, cols, zoom)
        chunk_data(con, s3, bucket, path, name, zoom, limit, geom_len_threshold)
        join_chunked(con, bucket, path, name)
    else:
        print("Writing single output")
        geom_to_h3(con, name, cols, zoom)
        con.sql(f'''
            SELECT *, UNNEST(h{zoom}) AS h{zoom}
            FROM t2
        ''').to_parquet(f"s3://{bucket}/{path}/hex/{name}.parquet")
