# %% [markdown]
# # Warning!
# Must run: `link_cad_stations_to_map_stations.ipynb` so Small Areas can be linked to Map stations via CAD stations

# %% [markdown]
# # Import dependencies
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import seaborn as sns

import dublin_electricity_network as den

show_plots = False
sns.set()
data_dir = Path("../data")

# %% [markdown]
# # Read Dublin Small Area boundaries
dublin_small_area_boundaries = gpd.read_file(
    data_dir / "dublin_small_area_boundaries.geojson",
    driver="GeoJSON",
).to_crs(epsg=2157)


# %% [markdown]
# # Read Dublin HV Station locations
esbmap_stations_dublin = gpd.read_file(
    data_dir / "esbmap_substations_linked_to_osm.geojson",
    driver="GeoJSON",
).to_crs(epsg=2157)

# %% [markdown]
# # Link Small Area Centroids to nearest CAD stations

# %%
dublin_small_area_centroids = dublin_small_area_boundaries.assign(
    geometry=lambda gdf: gdf.geometry.representative_point()
)
# %%
small_areas_linked_to_nearest_map_station = (
    den.join_nearest_points(dublin_small_area_centroids, esbmap_stations_dublin)
    .drop(columns=["geometry", "COUNTYNAME"])
    .merge(dublin_small_area_boundaries)
    .drop_duplicates(subset="SMALL_AREA")
)

# %% [markdown]
# # Plot
if show_plots:
    f, ax = plt.subplots(figsize=(120, 120))

    small_areas_linked_to_nearest_map_station.plot(
        ax=ax,
        edgecolor="white",
        color="teal",
    )
    small_areas_linked_to_nearest_map_station.apply(
        lambda x: ax.annotate(
            text=x["heatmap_station_name"],
            xy=x.geometry.centroid.coords[0],
            va="bottom",
            color="white",
            path_effects=[pe.withStroke(linewidth=2, foreground="orange")],
        ),
        axis=1,
    )

    map_stations_dublin.plot(ax=ax, color="black")
    map_stations_dublin.apply(
        lambda x: ax.annotate(
            text=x["heatmap_station_name"],
            xy=x.geometry.centroid.coords[0],
            color="white",
            path_effects=[pe.withStroke(linewidth=2, foreground="black")],
        ),
        axis=1,
    )

    # plt.legend(["Small Area Station IDs", "CAD Stations linked to Heat Map"], prop={'size': 25});
    plt.legend(list(range(5)), prop={"size": 25})

# %% [markdown]
# # Save
small_areas_linked_to_nearest_map_station.to_file(
    data_dir / "small-areas-linked-to-map-stations.geojson",
    driver="GeoJSON",
)

# %%
