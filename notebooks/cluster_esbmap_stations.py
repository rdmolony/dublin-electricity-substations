# %% [markdown]
# Adapted from: https://geoffboeing.com/2014/08/clustering-to-reduce-spatial-data-set-size/

# %%
from pathlib import Path

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from geopy.distance import great_circle
from shapely.geometry import MultiPoint
import seaborn as sns
from scipy.spatial import cKDTree

from dublin_electricity_network.join import join_nearest_points

sns.set()
data_dir = Path("../data")

# %% [markdown]
# # Read Dublin Small Area boundaries
dublin_boundary = gpd.read_file(
    data_dir / "dublin_boundary.geojson",
    driver="GeoJSON",
).to_crs(epsg=4326)

# %% [markdown]
# # Read Dublin HV Station locations

# %%
esbmap_stations_dublin = gpd.read_file(
    data_dir / "esbmap_substations_linked_to_osm.geojson",
    driver="GeoJSON",
).to_crs(epsg=4326)

# %% [markdown]
# # Cluster substations into N groups
# ... so only link loads to nearest large substation!

# %%
coords = esbmap_stations_dublin[["Longitude", "Latitude"]].to_numpy()

# %% [markdown]
# # DBSCAN

# %%
kms_per_radian = 6371.0088
max_km_distance_between_points = 2
epsilon = max_km_distance_between_points / kms_per_radian
db = DBSCAN(eps=epsilon, min_samples=1, algorithm="ball_tree", metric="haversine")
db.fit(np.radians(coords))
cluster_labels = db.labels_
num_clusters = len(set(cluster_labels))
clusters = pd.Series([coords[cluster_labels == n] for n in range(num_clusters)])
print("Number of clusters: {}".format(num_clusters))

# %%
def get_centermost_point(cluster):
    centroid = (MultiPoint(cluster).centroid.x, MultiPoint(cluster).centroid.y)
    centermost_point = min(cluster, key=lambda point: great_circle(point, centroid).m)
    return tuple(centermost_point)


centermost_points = clusters.map(get_centermost_point)

# %%
lat, long = zip(*centermost_points)
rep_points = (
    gpd.GeoDataFrame(geometry=gpd.points_from_xy(long, lat))
    .reset_index()
    .rename(columns={"index": "cluster_id"})
)

# %%
# f, ax = plt.subplots(figsize=(20, 20))
# rep_points.plot(ax=ax, c="#99cc99", edgecolor="None", alpha=0.7, markersize=120)
# esbmap_stations_dublin.plot(ax=ax, c="k", alpha=0.9, markersize=3)

# %%
def join_nearest_points(gdA, gdB):
    nA = np.array(list(gdA.geometry.apply(lambda x: (x.x, x.y))))
    nB = np.array(list(gdB.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(nB)
    dist, idx = btree.query(nA, k=1)
    gdB_nearest = gdB.iloc[idx].reset_index(drop=True)
    gdf = pd.concat(
        [
            gdA.reset_index(drop=True).drop(columns="geometry"),
            gdB_nearest,
        ],
        axis=1,
    )
    return gdf


esbmap_stations_linked_to_clusters = join_nearest_points(
    esbmap_stations_dublin,
    rep_points,
)

# %%
columns = ["cluster_id", "Installed Capacity MVA", "geometry"]
esbmap_stations_clustered = esbmap_stations_linked_to_clusters[columns].dissolve(
    by="cluster_id", aggfunc="sum", as_index=False
)

# %%
f, ax = plt.subplots(figsize=(20, 20))
dublin_boundary.plot(ax=ax, alpha=0.5)
esbmap_stations_clustered.plot(
    ax=ax, c="#99cc99", edgecolor="None", alpha=0.7, markersize=120
)
esbmap_stations_clustered.apply(
    lambda gdf: ax.annotate(
        gdf["Installed Capacity MVA"], xy=gdf.geometry.centroid.coords[0]
    ),
    axis="columns",
)
esbmap_stations_dublin.plot(ax=ax, c="k", alpha=0.9, markersize=3)

# %%
