# %% [markdown]
# # Warning!  Must run `get_data.py` to generate the data for this Notebook


# %% [markdown]
# # Load External Dependencies
from pathlib import Path

import geopandas as gpd
from osmnx.geometries import geometries_from_polygon
import seaborn as sns
from string_grouper import match_strings, match_most_similar

sns.set()
data_dir = Path("../data")

# %% [markdown]
# # Read Dublin HV Heat Map Stations
heatmap_stations = gpd.read_file(
    data_dir / "heatmap_stations.geojson",
    driver="GeoJSON",
)

# %% [markdown]
# # Read Dublin Boundary
dublin_boundary = gpd.read_file(
    data_dir / "dublin_boundary.geojson", driver="GeoJSON"
).to_crs(epsg=4326)
dublin_polygon = dublin_boundary.geometry.item()

# %% [markdown]
# # Get OSM substations within Dublin Boundary
osm_substations = geometries_from_polygon(dublin_polygon, tags={"substation": True})

# %%
osm_substation_points = osm_substations.assign(
    geometry=lambda gdf: gdf.geometry.centroid
)
# %% [markdown]
# # Standardise Station Names

# %%
heatmap_stations["station_name"] = (
    heatmap_stations["Station Name"].str.extract(r"(.+?)(?= \d)").fillna("").astype(str)
)
# %%
osm_substation_points["station_name"] = (
    osm_substation_points["name"].str.extract(r"(.+?)(?= \d)").fillna("").astype(str)
)

# %% [markdown]
# # Fuzzy match substation names

# %%
stations_in_common = match_strings(
    osm_substation_points["station_name"],
    heatmap_stations["station_name"],
).drop_duplicates()

# %%
osm_substation_points["heatmap_station_name"] = match_most_similar(
    heatmap_stations["station_name"],
    osm_substation_points["station_name"],
)

# %%
osm_substations_linked_to_heatmap = osm_substation_points.query(
    "heatmap_station_name != ''"
)

# %% [markdown]
# # Save
# ... can view result in QGIS to view comparison vs Heat Map Station Locations

osm_substations_linked_to_heatmap.drop(columns="nodes").to_file(
    data_dir / "osm_substations_linked_to_heatmap.geojson",
    driver="GeoJSON",
)

# %%
osm_substations.drop(columns="nodes").to_file(
    data_dir / "osm_substation.geojson", driver="GeoJSON"
)

# %%
osm_substation_points.drop(columns="nodes").to_file(
    data_dir / "osm_substation_points.geojson", driver="GeoJSON"
)
