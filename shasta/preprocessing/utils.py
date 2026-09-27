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


CATEGORY_TAGS = {
    'civic': {
        'courthouse', 'townhall', 'public_building', 'fire_station', 'police',
        'post_office', 'school', 'university', 'college', 'hospital', 'library',
        'public', 'government', 'civic', 'kindergarten',
    },
    'worship': {
        'place_of_worship', 'church', 'synagogue', 'mosque', 'temple', 'cathedral',
        'chapel', 'religious',
    },
    'commercial': {
        'commercial', 'retail', 'office', 'hotel', 'supermarket', 'kiosk',
        'restaurant', 'cafe', 'bank', 'shop',
    },
    'residential': {
        'house', 'apartments', 'residential', 'dormitory', 'detached', 'terrace',
        'semidetached_house', 'bungalow',
    },
    'industrial': {
        'garage', 'garages', 'parking', 'industrial', 'warehouse', 'service',
        'construction', 'hangar', 'carport',
    },
}


def building_category(building=None, amenity=None):
    """Sort an OSM building into civic, worship, commercial, residential, industrial or other."""
    for value in (amenity, building):
        for category, tags in CATEGORY_TAGS.items():
            if isinstance(value, str) and value in tags:
                return category
    return 'other'


def extract_building_footprints(osm_path):
    """Building outlines from the local .osm file.

    Returns a list of ``(outline, category)`` where ``outline`` is an (n, 2)
    [lat, lon] array and ``category`` comes from :func:`building_category`.
    """
    gdf = ox.features.features_from_xml(osm_path, tags={'building': True})
    footprints = []
    for _, row in gdf.iterrows():
        category = building_category(row.get('building'), row.get('amenity'))
        geometry = row.geometry
        for polygon in getattr(geometry, 'geoms', [geometry]):
            if polygon.geom_type == 'Polygon':
                lon, lat = polygon.exterior.xy
                footprints.append((np.column_stack([lat, lon]), category))
    return footprints


def save_buildings_map(osm_path):
    raise NotImplementedError


def extract_path_info(osm_path):
    raise NotImplementedError
