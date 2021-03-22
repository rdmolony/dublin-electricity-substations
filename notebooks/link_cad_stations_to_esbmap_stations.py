# %% [markdown]
# # Warning!
#  Must run `get_data.py` to generate the data for this Notebook

# %% [markdown]
# # Load External Dependencies
from pathlib import Path

import geopandas as gpd
import seaborn as sns

import dublin_electricity_network as den

sns.set()
data_dir = Path("../data")
cad_data = Path("/home/wsl-rowanm/Data/ESBdata_20200124")

# %% [markdown]
# # Read Dublin Local Authority Boundaries
dublin_admin_county_boundaries = den.read_dublin_admin_county_boundaries(
    data_dir / "dublin_admin_county_boundaries"
)

# %% [markdown]
# # Read 38kV, 110kV & 220kV Dublin stations from CAD data
cad_stations_dublin = gpd.read_file(
    data_dir / "cad_stations_dublin.geojson",
    driver="GeoJSON",
)

# %% [markdown]
# # Read Dublin OSM | Heat Map stations
esbmap_stations = gpd.read_file(
    data_dir / "esbmap_substations_linked_to_osm.geojson",
    driver="GeoJSON",
).to_crs(epsg=2157)

# %% [markdown]
# ## Link CAD stations to nearest Map station
cad_stations_linked_to_esbmap = den.join_nearest_points(
    cad_stations_dublin,
    esbmap_stations,
)


# %% [markdown]
# # Save

# %%
cad_stations_linked_to_esbmap.to_file(
    data_dir / "cad_stations_linked_to_nearest_esbmap_station.geojson",
    driver="GeoJSON",
)

# %%
cad_stations_linked_to_heatmap_lat_long = (
    cad_stations_linked_to_esbmap.assign(
        Latitude=lambda gdf: gdf.to_crs(epsg=4326).geometry.y,
        Longitude=lambda gdf: gdf.to_crs(epsg=4326).geometry.x,
        primary_voltage=lambda gdf: gdf["Level"].map({20: 38, 30: 110, 40: 220}),
    )
    .loc[:, ["station_name", "primary_voltage", "Latitude", "Longitude"]]
    .sort_values(["Latitude", "Longitude"])
)

# %%
cad_stations_linked_to_heatmap_lat_long.to_csv(
    data_dir / "cad_stations_linked_to_nearest_esbmap_station.csv",
    index=False,
)

# %%
