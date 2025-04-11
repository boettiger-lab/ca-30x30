from minio.error import S3Error
from cng.utils import *

import zipfile
import os
import subprocess

import geopandas as gpd
import ibis
from ibis import _

import rasterio
from rasterio.transform import xy
from shapely.geometry import Point
import numpy as np
from pyproj import Transformer

def info(folder, file, base_folder, bucket = "public-ca30x30"):
    """
    Extract minio path to upload/download data 
    """
    if (folder is None) & (base_folder is None):
        path = file
    else:
        path = os.path.join(base_folder, folder, file)
    # path = os.path.join(folder, file)
    return bucket, path 
    
def download(s3, folder, file, file_name = None, base_folder = "CBN/"):
    """
    Downloading file from minio
    """
    if not file_name: 
        file_name = file
    bucket, path = info(folder, file, base_folder)
    s3.fget_object(bucket, path , file_name) 
    return

def upload(s3, folder, file, base_folder = "CBN/"):
    """
    Uploading file from minio
    """
    bucket, path = info(folder, file, base_folder)
    s3.fput_object(bucket, path ,file) 
    return

def unzip(s3, folder, file, base_folder = "CBN/"):
    """
    Unzipping zip files 
    """
    download(s3, folder, file, base_folder)
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall()
    return 

def process_vector(s3, folder, file, file_name = None, gdf = None, crs="EPSG:4326", base_folder = "CBN/"):
    """
    Driver function to process vectors 
    """
    if gdf is None:
        gdf = gpd.read_file(file)
    if gdf.crs != crs:
        gdf = gdf.to_crs(crs)
    if gdf.geometry.name != 'geom':
        gdf = gdf.rename_geometry('geom')
    if file_name:
        file = file_name
    # upload_parquet(folder, file, gdf)
    name, ext = os.path.splitext(file)
    parquet_file = f"{name}{'.parquet'}"
    gdf.to_parquet(parquet_file)
    upload(s3, folder, parquet_file, base_folder)
    # return gdf.drop('geom',axis = 1).columns.to_list()
    return

def process_raster(s3, folder, file, file_name = None, base_folder = "CBN/"):
    """
    Driver function to process rasters 
    """
    if file_name:
        file = file_name
    name, ext = os.path.splitext(file)
    output_file = f"{name}_processed{ext}"
    output_cog_file = f"{name}_processed_COG{ext}"
    output_vector_file = f"{name}_processed.parquet"
    # Reproject raster
    if not exists_on_s3(s3, folder, output_file, base_folder):
        output_file = reproject_raster(file)
        upload(s3, folder, output_file, base_folder)
    else:
        print(f"{output_file} already exists on S3, skipping reprojection/upload.")

    # Make COG
    if not exists_on_s3(s3, folder, output_cog_file, base_folder):
        output_cog_file = make_cog(output_file)
        upload(s3, folder, output_cog_file, base_folder)
    else:
        print(f"{output_cog_file} already exists on S3, skipping COG conversion/upload.")

    # # Vectorize raster
    # if not exists_on_s3(s3, folder, output_vector_file, base_folder):
    #     output_vector_file, cols = make_vector(output_file)
    #     upload(s3, folder, output_vector_file, base_folder)
    # else:
    #     print(f"{output_vector_file} already exists on S3, skipping vectorization/upload.")
    #     # We still need column names
    #     gdf = gpd.read_parquet(output_vector_file)
    #     cols = gdf.drop('geom', axis=1).columns.to_list()
    # return cols
    return 
    
def reproject_raster(input_file, crs="EPSG:3310"):
    """
    Reproject rasters 
    """
    suffix = '_processed'
    name, ext = os.path.splitext(input_file)
    output_file = f"{name}{suffix}{ext}"
    command = [
        "gdalwarp",
        "-t_srs", crs,
        input_file,
        output_file 
        ]
    try:
        subprocess.run(command, check=True)
        print(f"Reprojection successful!")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during reprojection: {e}")
    return output_file 

def make_cog(input_file, crs="EPSG:4326"):
    """
    Converting TIF to COGs
    """
    suffix = '_COG'
    name, ext = os.path.splitext(input_file)
    output_file = f"{name}{suffix}{ext}"
    command = [
        "gdalwarp",
        "-t_srs", crs,
        "-of", "COG",
        input_file,
        output_file 
        ]
    try:
        subprocess.run(command, check=True)
        print(f"Successful!")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during processing: {e}")
    return output_file 

# def make_vector(input_file, crs="EPSG:4326"):
#     """
#     Converting rasters to vector formats in order to convert to h3
#     """
#     name, ext = os.path.splitext(input_file)
#     output_file = f"{name}.parquet"
    
#     with rasterio.open(input_file) as src:
#         band = src.read(1)  # read first band
#         mask = band != src.nodata  # mask out nodata
#         rows, cols = np.where(mask)
#         x, y = rasterio.transform.xy(src.transform, rows, cols, offset = "center")

#         # reproject 
#         if src.crs and src.crs.to_string() != crs:
#             transformer = Transformer.from_crs(src.crs, crs, always_xy=True)
#             x, y = transformer.transform(x, y)
#             crs_out = crs
#         else:
#             crs_out = src.crs

#         gdf = gpd.GeoDataFrame(
#             {"value": band[rows, cols]},
#             geometry=[Point(xy) for xy in zip(x, y)],
#             crs=crs_out
#         )

#     gdf.rename_geometry('geom', inplace=True)
#     gdf['id'] = np.arange(len(gdf))
#     gdf.to_parquet(output_file)
#     return output_file, gdf.drop('geom',axis = 1).columns.to_list()

def filter_raster(s3, folder, file, percentile):
    """
    Helper function to filter rasteres 
    """
    with rasterio.open(file) as src:
        data = src.read(1)  # Read the first band
        profile = src.profile
    # mask no data values
    masked_data = np.ma.masked_equal(data, src.nodata)

    # compute percentile/threshold 
    p = np.percentile(masked_data.compressed(),percentile)
    filtered = np.where(data >= p, data, src.nodata)
    name, ext = os.path.splitext(file)
    new_file = f"{name}{'_'}{percentile}{'percentile'}{ext}"

    profile.update(dtype=rasterio.float64)
    with rasterio.open(new_file, "w", **profile) as dst:
        dst.write(filtered, 1)
    process_raster(s3, folder, file)
    # return cols
    return

def convert_pmtiles(con, s3, folder, file, base_folder = "CBN/"):
    """
    Convert to PMTiles with tippecanoe 
    """
    name, ext = os.path.splitext(file)
    if ext != '.geojson':
            (con.read_parquet(file).execute().set_crs('epsg:3310')
             .to_crs('epsg:4326').to_file(name+'.geojson'))
    to_pmtiles(name+'.geojson', name+'.pmtiles', options = ['--extend-zooms-if-still-dropping'])
    upload(s3, folder, name+'.pmtiles', base_folder)
    return

def exists_on_s3(s3, folder, file, base_folder = "CBN/"):
    """
    Check if a file exists on S3
    """
    bucket, path = info(folder, file, base_folder)
    try:
        s3.stat_object(bucket, path)
        return True
    except S3Error:
        return False

