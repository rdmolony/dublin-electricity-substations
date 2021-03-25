# %% [markdown]
# Adapted from: https://geoffboeing.com/2014/08/clustering-to-reduce-spatial-data-set-size/

# %%
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
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
esbmap_capacity_columns = [
    "slr_load_mva",
    "installed_capacity_mva",
    "planned_capacity_mva",
    "demand_available_mva",
    "gen_available_firm_mva",
]

# %%
columns = esbmap_capacity_columns + ["geometry"]
esbmap_stations_dublin = (
    gpd.read_file(
        data_dir / "esbmap_substations_linked_to_osm.geojson",
        driver="GeoJSON",
    )
    .to_crs(epsg=2157)
    .assign(
        slr_load_mva=lambda gdf: gdf["SLR Load MVA"].round(),
        installed_capacity_mva=lambda gdf: gdf["Installed Capacity MVA"].round(),
        planned_capacity_mva=lambda gdf: gdf["Demand Planning Capacity"].round(),
        demand_available_mva=lambda gdf: gdf["Demand Available MVA"].round(),
        gen_available_firm_mva=lambda gdf: gdf["Gen Available Firm"].round(),
    )
    .loc[:, columns]
)

# %% [markdown]
# # Cluster substations into N groups
# ... so only link loads to nearest large substation!

# %%
coords = (
    esbmap_stations_dublin.assign(
        x=lambda gdf: gdf.geometry.x,
        y=lambda gdf: gdf.geometry.y,
    )
    .loc[:, ["x", "y"]]
    .to_numpy()
)

# %% [markdown]
# # Cluster Substations

# %%
keep_columns = esbmap_capacity_columns + ["cluster_id", "geometry"]

# %%
esbmap_stations_dublin["cluster_id"] = cluster_itm_coords(
    esbmap_stations_dublin,
    coords,
    how="knearest",
    n_clusters=10,
    keep_columns=keep_columns,
)

# %%
esbmap_stations_clustered = (
    esbmap_stations_dublin[keep_columns]
    .dissolve(by="cluster_id", aggfunc="sum", as_index=False)
    .assign(geometry=lambda gdf: gdf.geometry.centroid)
)


# %%
def plot_clusters(boundary, unclustered, clustered, column_name):
    f, ax = plt.subplots(figsize=(20, 20))
    boundary.plot(ax=ax, alpha=0.5)
    clustered.plot(ax=ax, c="#99cc99", edgecolor="None", alpha=0.7, markersize=120)
    clustered.apply(
        lambda gdf: ax.annotate(
            "ID = " + str(gdf["cluster_id"]),
            xy=gdf.geometry.centroid.coords[0],
            va="top",
            path_effects=[pe.withStroke(linewidth=4, foreground="white")],
        ),
        axis="columns",
    )
    clustered.apply(
        lambda gdf: ax.annotate(
            str(gdf[column_name]) + " MVA",
            xy=gdf.geometry.centroid.coords[0],
            va="bottom",
            path_effects=[pe.withStroke(linewidth=4, foreground="white")],
        ),
        axis="columns",
    )
    unclustered.plot(ax=ax, c="k", alpha=0.9, markersize=3)
    return f, ax


# %%
f, ax = plot_clusters(
    dublin_boundary,
    esbmap_stations_dublin,
    esbmap_stations_clustered,
    "demand_available_mva",
)
plt.title("Available capacity per substation cluster", fontsize=20)
f.savefig(data_dir / "Available Capacity per Substation Cluster.png")

# %%
esbmap_stations_clustered.to_file(
    data_dir / "esbmap_stations_clustered.geojson", driver="GeoJSON"
)
