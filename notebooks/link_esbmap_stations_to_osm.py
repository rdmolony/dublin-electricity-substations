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


def points_xy_to_gdf(df, x, y):

    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x], df[y]))


# %% [markdown]
# # Read Dublin HV ESB Map Stations
esbmap_stations = gpd.read_file(
    data_dir / "esbmap_stations.geojson",
    driver="GeoJSON",
)

# %% [markdown]
# # Read Dublin Boundary
dublin_boundary = gpd.read_file(
    data_dir / "dublin_boundary.geojson", driver="GeoJSON"
).to_crs(epsg=2157)

# %%
dublin_polygon = dublin_boundary.to_crs(epsg=4326).geometry.item()

# %% [markdown]
# # Get OSM substations within Dublin Boundary
osm_substations = geometries_from_polygon(
    dublin_polygon, tags={"substation": True}
).to_crs(epsg=2157)

# %%
useful_osm_columns = [
    "name",
    "addr:street",
    "location",
    "fixme",
    "operator",
    "power",
    "voltage",
    "voltage:primary",
    "voltage:secondary",
    "geometry",
]
osm_substation_points = osm_substations.assign(
    geometry=lambda gdf: gdf.geometry.centroid
).loc[:, useful_osm_columns]

# %% [markdown]
# # Standardise Station Names

# %%
esbmap_stations["esbmap_station_name"] = (
    esbmap_stations["Station Name"]
    .str.extract(r"(.*?)(?= \d|$)")
    .fillna("")
    .astype(str)
    .replace(
        {
            "Inchicore North": "Inchicore",
            "Inchicore Central": "Inchicore",
            "Milltown (dr)": "Milltown",
            "Grange (dr)": "Grange",
            "Newmarket (dr)": "Newmarket",
        }
    )
)
# %%
osm_substation_points["osm_station_name"] = (
    osm_substation_points["name"]
    .str.extract(r"(.*?)(?= \d|$)")
    .fillna("")
    .astype(str)
    .replace(
        {
            "Misery Hill Substation": "Misery Hill",
            "Merrion Square East": "Merrion Square",
            "Grange Castle East": "Grange Castle",
            "Grange Castle West": "Grange Castle",
            "Palmerston": "Palmerstown",
            "Ballycoolen": "Ballycoolin",
            "Wolfe Tone": "Wolfe Tone Street",
            "Phibsborough": "Phibsboro",
            "Old Bawn": "Oldbawn",
        }
    )
)

# %% [markdown]
# # Fuzzy match substation names
# ... and replace matching names with a unique value across data sets

# %%
stations_in_common = match_strings(
    esbmap_stations["esbmap_station_name"],
    osm_substation_points["osm_station_name"],
    min_similarity=0.5,
).drop_duplicates()

display(stations_in_common.query("similarity < 0.99"))

# %%
# esbmap_stations["most_similar_osm_station_name"] = match_most_similar(
#     osm_substation_points["osm_station_name"],
#     esbmap_stations["esbmap_station_name"],
# )


# %% [markdown]
# # Merge ESB Map with OSM via matching station names
esbmap_substations_linked_to_osm = (
    esbmap_stations.drop(columns="geometry")
    .merge(
        osm_substation_points,
        left_on="esbmap_station_name",
        right_on="osm_station_name",
        how="left",
        indicator=True,
    )
    .assign(
        in_osm=lambda gdf: gdf["_merge"].map({"both": True, "left_only": False}),
        Latitude=lambda gdf: gdf.to_crs(epsg=4326).geometry.y.fillna(gdf["Latitude"]),
        Longitude=lambda gdf: gdf.to_crs(epsg=4326).geometry.x.fillna(gdf["Longitude"]),
    )  # Where OSM location found replace Lat | Long with OSM Location
    .drop(columns="_merge")
    .pipe(points_xy_to_gdf, x="Longitude", y="Latitude")
)

# %% [markdown]
# # Find ESB Map stations that aren't in OSM

# %%
columns = ["esbmap_station_name", "osm_station_name", "_merge"]
esbmap_stations_not_in_osm_names = esbmap_substations_linked_to_osm.query(
    "in_osm == False"
)

# %%
match_strings(
    esbmap_stations_not_in_osm_names["esbmap_station_name"],
    osm_substation_points["addr:street"].fillna("").astype(str),
    min_similarity=0.5,
)

# %%
match_strings(
    esbmap_stations_not_in_osm_names["esbmap_station_name"],
    osm_substation_points["name"].fillna("").astype(str),
    min_similarity=0.5,
)

# %% [markdown]
# # Save
# ... can view result in QGIS to view comparison vs ESB Map Station Locations

# %%
esbmap_substations_linked_to_osm.to_file(
    data_dir / "esbmap_substations_linked_to_osm.geojson",
    driver="GeoJSON",
)

# %%
columns = ["Latitude", "Longitude", "esbmap_station_name"]
esbmap_substations_linked_to_osm.query("in_osm == True").loc[:, columns].sort_values(
    "esbmap_station_name"
).to_csv(
    data_dir / "esbmap_substations_linked_to_osm.csv",
    index=False,
)

# %%
columns = ["Latitude", "Longitude", "esbmap_station_name"]
esbmap_substations_linked_to_osm.query("in_osm == False").loc[:, columns].sort_values(
    "esbmap_station_name"
).to_csv(
    data_dir / "esbmap_substations_not_linked_to_osm.csv",
    index=False,
)

# %%
osm_substations.to_crs(epsg=4326).drop(columns="nodes").to_file(
    data_dir / "osm_substation.geojson", driver="GeoJSON"
)

# %%
osm_substation_points.to_crs(epsg=4326).to_file(
    data_dir / "osm_substation_points.geojson", driver="GeoJSON"
)
