# %%
from os import listdir
from pathlib import Path
from shutil import unpack_archive

import geopandas as gpd
from shapely.geometry import box

import dublin_electricity_network as den

data_dir = Path("../data")
cad_data = Path("/home/wsl-rowanm/Data/ESBdata_20200124")

# %% [markdown]
# # Get Dublin Boundary
den.download(
    url="https://zenodo.org/record/4577018/files/dublin_boundary.geojson",
    to_filepath=str(data_dir / "dublin_boundary.geojson"),
)
# %%
dublin_boundary = gpd.read_file(data_dir / "dublin_boundary.geojson")

# %% [markdown]
# # Get Dublin LA boundaries

# %%
den.download(
    url="https://zenodo.org/record/4446778/files/dublin_admin_county_boundaries.zip",
    to_filepath=str(data_dir / "dublin_admin_county_boundaries.zip"),
)

# %%
unpack_archive(
    data_dir / "dublin_admin_county_boundaries.zip",
    data_dir,
)

# %%
dublin_admin_county_boundaries = den.read_dublin_admin_county_boundaries(
    data_dir / "dublin_admin_county_boundaries"
)


# %% [markdown]
# # Get Dublin HV Heat Map stations

# %%
den.download(
    url="https://esbnetworks.ie/docs/default-source/document-download/heatmap-download-version-nov-2020.xlsx",
    to_filepath=str(data_dir / "heatmap-download-version-nov-2020.xlsx"),
)

# %%
esbmap_stations_ireland = den.read_heatmap(
    data_dir / "heatmap-download-version-nov-2020.xlsx"
)

# %%
esbmap_stations_dublin = gpd.sjoin(
    esbmap_stations_ireland,
    dublin_admin_county_boundaries,
    op="within",
).drop(columns="index_right")

# %%
esbmap_stations_dublin_hv = esbmap_stations_dublin.query("station_name != 'mv/lv'")

# %%
esbmap_stations_dublin_hv.to_file(
    data_dir / "esbmap_stations.geojson",
    driver="GeoJSON",
)

# %% [markdown]
# # Get 38kV, 110kV & 220kV Dublin stations from CAD data
# .. must be downloaded from the Codema Google Shared Drive or <span style="color:red">**requested from the ESB**</span>

# %%
hv_network_dirpath = cad_data / "Dig Request Style" / "HV Data"
hv_network_filepaths = [
    hv_network_dirpath / filename for filename in listdir(hv_network_dirpath)
]
# %%
cad_stations_ireland = den.read_network(hv_network_filepaths, levels=[20, 30, 40])
# %%
cad_stations_dublin = gpd.sjoin(
    cad_stations_ireland,
    dublin_admin_county_boundaries,
    op="within",
).drop(columns=["index_right", "COUNTYNAME"])
# %%
cad_stations_dublin.to_file(data_dir / "cad_stations_dublin.geojson", driver="GeoJSON")

# %% [markdown]
# # Get Dublin Small Area boundaries

# %%
small_area_boundaries_filepath = (
    data_dir
    / "Small_Areas_Ungeneralised_-_OSi_National_Statistical_Boundaries_-_2015-shp"
)
# %%
den.download(
    url="https://opendata.arcgis.com/datasets/c85e610da1464178a2cd84a88020c8e2_3.zip",
    to_filepath=str(small_area_boundaries_filepath.with_suffix(".zip")),
)
# %%
unpack_archive(
    small_area_boundaries_filepath.with_suffix(".zip"),
    small_area_boundaries_filepath,
)

# %% [markdown]
# # Get Dublin MV Network Lines

# %%
ireland_mv_index = den.read_mv_index(cad_data / "Ancillary Data" / "mv_index.dgn")

# %%
dublin_boundary = (
    gpd.GeoSeries(box(695000, 715000, 740000, 771000)).rename("geometry").to_frame()
)
# %%
dublin_mv_index = gpd.sjoin(
    ireland_mv_index, dublin_boundary.to_crs(epsg=2157), op="within"
)
# %%
dublin_mv_network_filepaths = [
    cad_data / "Dig Request Style" / "MV-LV Data" / f"{index}.dgn"
    for index in dublin_mv_index.Text
]
# %%
dublin_mv_network_lines = (
    den.read_network(dublin_mv_network_filepaths, levels=[10, 11, 14])
    .reset_index(drop=True)
    .explode()
)
# %%
dublin_mv_network_lines.to_file(
    data_dir / "dublin_mv_network_lines.geojson", driver="GeoJSON"
)

# %%
