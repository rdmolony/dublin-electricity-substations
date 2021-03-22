# %% [markdown]
# Adapted from: https://geoffboeing.com/2014/08/clustering-to-reduce-spatial-data-set-size/

# %%
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from dublin_electricity_network.cluster import cluster_itm_coords

sns.set()
data_dir = Path("../data")

# %% [markdown]
# # Read Dublin Small Area boundaries
dublin_boundary = gpd.read_file(
    data_dir / "dublin_boundary.geojson",
    driver="GeoJSON",
).to_crs(epsg=2157)

# %% [markdown]
# # Read Dublin HV Station locations

# %%
esbmap_stations_dublin = gpd.read_file(
    data_dir / "esbmap_substations_linked_to_osm.geojson",
    driver="GeoJSON",
).to_crs(epsg=2157)

# %% [markdown]
# # Cluster substations into N groups
# ... so only link loads to nearest large substation!

# %%
# coords = esbmap_stations_dublin[["Latitude", "Longitude"]].to_numpy()
coords = (
    esbmap_stations_dublin.assign(
        x=lambda gdf: gdf.geometry.x,
        y=lambda gdf: gdf.geometry.y,
    )
    .loc[:, ["x", "y"]]
    .to_numpy()
)

# %% [markdown]
# # Cluster Substations via DBSCAN

# %%
esbmap_stations_clustered_dbscan = cluster_itm_coords(
    esbmap_stations_dublin,
    coords,
    how="dbscan",
    max_km_distance_between_points=2500,
    keep_columns=["cluster_id", "Installed Capacity MVA", "geometry"],
)

# %%
esbmap_stations_clustered_knearest = cluster_itm_coords(
    esbmap_stations_dublin,
    coords,
    how="knearest",
    n_clusters=10,
    keep_columns=["cluster_id", "Installed Capacity MVA", "geometry"],
)

# %%
f, ax = plt.subplots(figsize=(20, 20))
dublin_boundary.plot(ax=ax, alpha=0.5)
esbmap_stations_clustered_knearest.plot(
    ax=ax, c="#99cc99", edgecolor="None", alpha=0.7, markersize=120
)
esbmap_stations_clustered_knearest.apply(
    lambda gdf: ax.annotate(
        gdf["Installed Capacity MVA"], xy=gdf.geometry.centroid.coords[0]
    ),
    axis="columns",
)
esbmap_stations_dublin.plot(ax=ax, c="k", alpha=0.9, markersize=3)

# %%

# %%
