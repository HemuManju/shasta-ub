from pathlib import Path

import numpy as np
import pandas as pd


import networkx as nx
import osmnx as ox


def extract_building_info(osm_path, save_fig=False):
    """Perfrom initial building setup."""
    read_path = osm_path
    G = ox.graph_from_xml(read_path, retain_all=True)

    # Read building footprints from the local file (no network access needed)
    gdf = ox.features.features_from_xml(read_path, tags={'building': True})
    gdf = gdf[gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
    buildings_proj = ox.projection.project_gdf(gdf, to_crs="EPSG:4326").to_crs(4328)

    # Building Info
    building_info = buildings_proj.copy()

    # Add more information
    # Save the dataframe representing buildings
    building_info['lon'] = buildings_proj['geometry'].centroid.x
    building_info['lat'] = buildings_proj['geometry'].centroid.y
    building_info['area'] = buildings_proj.area
    building_info['perimeter'] = buildings_proj.length
    try:
        building_info.loc[:, 'height'] = buildings_proj['height']
    except KeyError:
        building_info.loc[:, 'height'] = 10  # assumption
    building_info['id'] = np.arange(len(buildings_proj))

    if save_fig:
        save_path = Path(osm_path)
        ox.plot_graph(G)
        ox.plot.plot_footprints(
            buildings_proj, save=True, filepath=save_path.with_suffix('.jpg')
        )

    return building_info


def save_buildings_map(osm_path):
    raise NotImplementedError


def extract_path_info(osm_path):
    raise NotImplementedError
