# %% [markdown]
# # Warning!
# Must run: `link_cad_stations_to_map_stations.ipynb` so Small Areas can be linked to Map stations via CAD stations

# %% [markdown]
# # Import dependencies
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import momepy
import networkx as nx

import dublin_electricity_network as den

data_dir = Path("../data")
cad_data = Path("/home/wsl-rowanm/Data/ESBdata_20200124")
show_plots = False

# %% [markdown]
# # Read Dublin Small Area boundaries
dublin_small_area_boundaries = den.read_dublin_small_areas(
    data_dir
    / "Small_Areas_Ungeneralised_-_OSi_National_Statistical_Boundaries_-_2015-shp"
)

# %% [markdown]
# # Read Local Authority boundaries
dublin_admin_county_boundaries = den.read_dublin_admin_county_boundaries(
    data_dir / "dublin_admin_county_boundaries"
)

# %% [markdown]
# # Read Dublin MV Network Lines
dublin_mv_network_lines = gpd.read_file(
    data_dir / "dublin_mv_network_lines.geojson", driver="GeoJSON"
)

# %% [markdown]
# # Read Dublin HV Station locations
hv_stations_dublin = gpd.read_file(
    data_dir / "cad_stations_dublin.geojson",
    driver="GeoJSON",
)


# %% [markdown]
# # Link Each Small Area Centroid to a Station via Network
# Use `networkx` to find the station that is closest along the network to each small area centroid:
# - Convert `geopandas` `GeoDataFrame` to `networkx` `MultiGraph` via `momepy` for network analysis
# - Extract the largest unbroken network
# - Extract all stations and small areas near the network
# - Trace the path from each small area centroid to the nearest station along the network

# %%
G = momepy.gdf_to_nx(dublin_mv_network_lines, approach="primal")

# %%
G_largest = den.get_largest_subgraph(G)

# %%
G_largest_nodes, G_largest_edges, G_largest_sw = momepy.nx_to_gdf(
    G_largest, points=True, lines=True, spatial_weights=True
)

# %%
G_largest_edges_buffered = (
    G_largest_edges[["geometry"]]
    .assign(geometry=lambda gdf: gdf.buffer(750), x=0)
    .dissolve(by="x")[["geometry"]]
)

# %%
small_areas_near_g_largest = den.centroids_within(
    dublin_small_area_boundaries,
    G_largest_edges_buffered,
)

# %%
hv_stations_near_g_largest = (
    gpd.sjoin(
        hv_stations_dublin,
        G_largest_edges_buffered,
        op="within",
    )
    .drop(columns="index_right")
    .reset_index(drop=True)
)

# %%
hv_stations_snapped_to_g_largest = den.snap_points_to_network(
    G_largest, hv_stations_near_g_largest
)

# %%
shortest_paths = den.get_network_paths_between_points(
    G=G_largest,
    orig_points=small_areas_near_g_largest,
    dest_points=hv_stations_snapped_to_g_largest,
)

# %%
if show_plots:
    n = 0  # change 'n' to change the path to be displayed
    f, ax = plt.subplots(figsize=(15, 15))

    dublin_admin_county_boundaries.plot(edgecolor="red", facecolor="orange", ax=ax)

    positions = {z: [z[0], z[1]] for z in list(G.nodes)}
    nx.draw(
        G_largest, positions, node_size=5, ax=ax, node_color="none", edge_color="teal"
    )

    x, y = zip(*shortest_paths[n][1])
    ax.plot(x, y, c="k", lw=20, alpha=0.5)
    ax.scatter(
        small_areas_near_g_largest.iloc[n].geometry.centroid.x,
        small_areas_near_g_largest.iloc[n].geometry.centroid.y,
        color="green",
        s=50,
    )
    ax.scatter(x[0], y[0], color="red", s=50)
    ax.scatter(x[-1], y[-1], color="green", s=50)
    ax.scatter(
        hv_stations_snapped_to_g_largest.geometry.x,
        hv_stations_snapped_to_g_largest.geometry.y,
        color="black",
        s=10,
    )

# %% [markdown]
# # Link Small Areas to stations

# %%
small_areas_linked_to_stations_via_network = den.extract_nearest_dest(
    shortest_paths,
    small_areas_near_g_largest,
    hv_stations_snapped_to_g_largest,
).drop_duplicates(subset="SMALL_AREA")


# %%
small_areas_remaining_centroids = gpd.GeoDataFrame(
    dublin_small_area_boundaries.merge(
        small_areas_near_g_largest, how="left", indicator=True
    )
    .query("`_merge` == 'left_only'")
    .drop(columns="_merge")
    .assign(geometry=lambda gdf: gdf.geometry.centroid)
)

# %%
small_areas_linked_to_stations_via_nearest = (
    den.join_nearest_points(small_areas_remaining_centroids, hv_stations_dublin)
    .drop(columns=["geometry", "COUNTYNAME"])
    .merge(dublin_small_area_boundaries)
    .drop_duplicates(subset="SMALL_AREA")
)

# %%
small_areas_linked_to_stations = pd.concat(
    [
        small_areas_linked_to_stations_via_network,
        small_areas_linked_to_stations_via_nearest,
    ]
).drop_duplicates(subset="SMALL_AREA")

# %%
if show_plots:

    f, ax = plt.subplots(figsize=(120, 120))

    small_areas_linked_to_stations_via_network.plot(
        ax=ax,
        edgecolor="white",
        color="teal",
    )
    small_areas_linked_to_stations_via_network.apply(
        lambda x: ax.annotate(
            text=x["station_id"],
            xy=x.geometry.centroid.coords[0],
            va="bottom",
            color="white",
            path_effects=[pe.withStroke(linewidth=2, foreground="orange")],
        ),
        axis=1,
    )
    small_areas_linked_to_stations_via_nearest.plot(
        ax=ax,
        edgecolor="white",
        facecolor="cyan",
    )
    small_areas_linked_to_stations_via_nearest.apply(
        lambda x: ax.annotate(
            text=x["station_id"],
            xy=x.geometry.centroid.coords[0],
            va="bottom",
            color="white",
            path_effects=[pe.withStroke(linewidth=2, foreground="brown")],
        ),
        axis=1,
    )

    G_positions = {z: [z[0], z[1]] for z in list(G.nodes)}
    nx.draw(G, G_positions, node_size=5, ax=ax, node_color="none", edge_color="blue")
    G_largest_positions = {z: [z[0], z[1]] for z in list(G_largest.nodes)}
    nx.draw(
        G_largest,
        G_largest_positions,
        node_size=5,
        ax=ax,
        node_color="none",
        edge_color="red",
    )

    hv_stations_dublin.plot(ax=ax, color="black")
    hv_stations_dublin.apply(
        lambda x: ax.annotate(
            text=x["station_id"],
            xy=x.geometry.centroid.coords[0],
            va="top",
            color="white",
            path_effects=[pe.withStroke(linewidth=2, foreground="black")],
        ),
        axis=1,
    )
    hv_stations_dublin.apply(
        lambda x: ax.annotate(
            text=x["station_name"],
            xy=x.geometry.centroid.coords[0],
            va="bottom",
            color="white",
            path_effects=[pe.withStroke(linewidth=2, foreground="black")],
        ),
        axis=1,
    )

    # plt.legend(["Small Area Station IDs", "CAD Stations linked to Heat Map"], prop={'size': 25});
    plt.legend(list(range(5)), prop={"size": 25})

# %% [markdown]
#
# # Save

# %%
small_areas_linked_to_stations.to_file(
    data_dir / "small-areas-linked-to-map-stations.geojson",
    driver="GeoJSON",
)
