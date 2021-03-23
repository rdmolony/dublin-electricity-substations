# %%
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

import dublin_electricity_network as den
from dublin_electricity_network.cluster import cluster_itm_coords

sns.set()
data_dir = Path("../data")
power_factor = 0.95


def read_xlsx_as_gdf(filepath, x, y, crs, *args, **kwargs):
    df = pd.read_excel(filepath, engine="openpyxl", *args, **kwargs)
    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df[x], df[y], crs=crs)
    ).drop(columns=[x, y])


# %%
esbmap_stations_clustered = gpd.read_file(
    data_dir / "esbmap_stations_clustered.geojson",
    driver="GeoJSON",
)

# %%
dublin_boundary = gpd.read_file(
    data_dir / "dublin_boundary.geojson",
    driver="GeoJSON",
)

# %%
dublin_small_area_boundaries = gpd.read_file(
    data_dir / "dublin_small_area_boundaries.geojson",
    driver="GeoJSON",
)

# %%
ireland_small_area_statistics = (
    pd.read_csv(
        data_dir / "SAPS2016_SA2017.csv",
    )
    .assign(SMALL_AREA=lambda df: df["GEOGID"].str[7:])
    .rename(columns={"T6_2_TH": "total_hh"})
    .loc[:, ["SMALL_AREA", "total_hh"]]
)

# %%
data_centre_loads = (
    read_xlsx_as_gdf(
        data_dir / "data_centre_loads.xlsx",
        x="IG_X",
        y="IG_Y",
        crs="EPSG:29903",
    )
    .to_crs(epsg=2157)
    .assign(
        estimated_data_centre_load_mva=lambda gdf: gdf.eval(
            "`2021 - Annual Electricity Demand (kWh) at 55% Utilisation of Capacity`"
            "* (10**-3) * @power_factor / 8784"
        ).round(),
        installed_data_centre_capacity_mva=lambda gdf: gdf.eval(
            "`Installed Elec Capacity (kW)` * (10**-3) * @power_factor"
        ).round(),
    )
    .pipe(
        den.join_nearest_points, esbmap_stations_clustered[["cluster_id", "geometry"]]
    )
    .loc[:, ["cluster_id", "installed_data_centre_capacity_mva", "geometry"]]
)

# %%
commercial_buildings = (
    gpd.read_file(
        data_dir / "commercial_buildings_2015.geojson",
        driver="GeoJSON",
    )
    .query(
        "`Reference Benchmark Used` != 'None'"
        " and `Reference Benchmark Used`.notnull()"
        " and `Reference Benchmark Used` != 'Unknown'"
    )
    .assign(
        industrial=lambda gdf: gdf["Reference Benchmark Used"]
        .map(
            {
                "Manufacturing: General (Table: 20.20)": True,
                "Food: Cold (Table 20.20) ": True,
                "Food: Cooked (Table: 20.20) ": True,
                "Cold Storage (TM:46)": True,
                "Laboratories (Table 20.20)": True,
                "Engineering (Table 20.20)": True,
                "Furnace/Foundry (Table 20.20)": True,
            }
        )
        .fillna(False)
    )
)

# %% [markdown]
# # Link Small Areas stations to Substation Cluster
dublin_small_area_boundaries["cluster_id"] = den.join_nearest_points(
    dublin_small_area_boundaries.assign(geometry=lambda gdf: gdf["geometry"].centroid),
    esbmap_stations_clustered[["cluster_id", "geometry"]],
).loc[:, "cluster_id"]

# %%
dublin_small_area_boundaries["total_hh"] = dublin_small_area_boundaries.merge(
    ireland_small_area_statistics
).loc[:, "total_hh"]

# %%
esbmap_stations_clustered["residential_buildings"] = (
    dublin_small_area_boundaries.groupby("cluster_id")["total_hh"].sum().round()
)

# %%
peak_demand_mva_lower = 1.5 * (10 ** -3) * power_factor
esbmap_stations_clustered["resi_peak_mva_at_1_5kw"] = esbmap_stations_clustered.eval(
    "residential_buildings * @peak_demand_mva_lower"
).round()

peak_demand_mva_upper = 2.5 * (10 ** -3) * power_factor
esbmap_stations_clustered["resi_peak_mva_at_2_5kw"] = esbmap_stations_clustered.eval(
    "residential_buildings * @peak_demand_mva_upper"
).round()

# %% [markdown]
# # Aggregate Non-Residential Buildings to Substation Cluster

# %%
commercial_buildings["cluster_id"] = den.join_nearest_points(
    commercial_buildings,
    esbmap_stations_clustered[["cluster_id", "geometry"]],
).loc[:, "cluster_id"]

# %%
esbmap_stations_clustered["non_residential_buildings"] = (
    commercial_buildings.query("industrial == False").groupby("cluster_id").size()
)

esbmap_stations_clustered["industrial_buildings"] = (
    commercial_buildings.query("industrial == True").groupby("cluster_id").size()
)


# %% [markdown]
# # Aggregate Data Centre capacities to cluster_id

# %%
esbmap_stations_clustered["data_centres"] = (
    esbmap_stations_clustered.merge(
        data_centre_loads.groupby("cluster_id", as_index=False).size(),
        how="left",
    )
    .fillna(0)
    .loc[:, "size"]
)

# %%
esbmap_stations_clustered["installed_data_centre_capacity_mva"] = (
    esbmap_stations_clustered.merge(
        data_centre_loads.groupby("cluster_id", as_index=False)[
            "installed_data_centre_capacity_mva"
        ]
        .sum()
        .round(),
        how="left",
    )
    .fillna(0)
    .loc[:, "installed_data_centre_capacity_mva"]
)

# %% [markdown]
# # Estimate Data Centre Loads at each cluster
utilisation_percent_lower = 0.45
esbmap_stations_clustered[
    "data_centre_load_mva_at_45_pc_utilisation"
] = esbmap_stations_clustered.eval(
    "installed_data_centre_capacity_mva * @utilisation_percent_lower"
).round()

utilisation_percent_upper = 0.55
esbmap_stations_clustered[
    "data_centre_load_mva_at_55_pc_utilisation"
] = esbmap_stations_clustered.eval(
    "installed_data_centre_capacity_mva * @utilisation_percent_upper"
).round()


# %% [markdown]
# # Get remaining Load at each cluster
esbmap_stations_clustered["remaining_load_mva_lower"] = esbmap_stations_clustered.eval(
    "slr_load_mva - (resi_peak_mva_at_2_5kw + data_centre_load_mva_at_55_pc_utilisation)"
)

esbmap_stations_clustered["remaining_load_mva_upper"] = esbmap_stations_clustered.eval(
    "slr_load_mva - (resi_peak_mva_at_1_5kw + data_centre_load_mva_at_45_pc_utilisation)"
)


# %% [markdown]
# # Plot
def plot_clusters(boundary, clustered, column_name):
    f, ax = plt.subplots(figsize=(20, 20))
    boundary.plot(ax=ax, alpha=0.5)
    clustered.plot(ax=ax, c="#99cc99", edgecolor="None", alpha=0.7, markersize=120)
    clustered.apply(
        lambda gdf: ax.annotate(
            "ID=" + str(gdf["cluster_id"]),
            xy=gdf.geometry.centroid.coords[0],
            va="top",
        ),
        axis="columns",
    )
    clustered.apply(
        lambda gdf: ax.annotate(
            gdf[column_name],
            xy=gdf.geometry.centroid.coords[0],
            va="bottom",
        ),
        axis="columns",
    )
    return ax


plot_clusters(
    dublin_boundary,
    esbmap_stations_clustered,
    "remaining_load_mva_upper",
)

# %%
esbmap_stations_clustered.to_csv(data_dir / "SUBSTATION_LOADS.csv", index=False)
