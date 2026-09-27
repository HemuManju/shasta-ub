import warnings

from pathlib import Path

import numpy as np
import osmnx as ox
import pandas as pd
import networkx as nx

from shasta.assets import get_asset_path
from shasta.preprocessing.utils import extract_building_footprints, extract_building_info

ROAD_TYPES = frozenset({
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
    'residential', 'living_street', 'service',
    'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link',
})


def _is_road(highway, road_types):
    values = highway if isinstance(highway, (list, tuple)) else [highway]
    return any(value in road_types for value in values)


def road_graph(osm_path, road_types=ROAD_TYPES):
    """Street graph from an .osm file using only ``road_types`` (no footpaths, plazas or
    building outlines), reduced to its largest connected component."""
    G = ox.graph_from_xml(osm_path, simplify=False, bidirectional='walk')
    drop = [
        (u, v, k)
        for u, v, k, data in G.edges(keys=True, data=True)
        if not _is_road(data.get('highway'), road_types)
    ]
    G.remove_edges_from(drop)
    G.remove_nodes_from(list(nx.isolates(G)))
    if G.number_of_edges() == 0:
        raise ValueError(f"No roads of type {sorted(road_types)} found in {osm_path}")
    G = ox.simplification.simplify_graph(G)
    return ox.truncate.largest_component(G, strongly=True)


class Map:
    def __init__(self) -> None:
        return None

    def _affine_transformation_and_graph(self):
        """Performs initial conversion of the lat lon to cartesian"""
        # Graph
        read_path = self.asset_path + '/map.osm'
        road_types = (self.experiment_config or {}).get('road_types') or ROAD_TYPES
        G = road_graph(read_path, frozenset(road_types))
        self.node_graph = nx.convert_node_labels_to_integers(G)

        # Transformation matrix
        read_path = self.asset_path + '/coordinates.csv'
        points = pd.read_csv(read_path)
        target = points[['x', 'z']].values
        source = points[['lat', 'lon']].values

        # Pad the points with ones
        X = np.hstack((source, np.ones((source.shape[0], 1))))
        Y = np.hstack((target, np.ones((target.shape[0], 1))))
        self.A, res, rank, s = np.linalg.lstsq(X, Y, rcond=None)

        return None

    def _setup_building_info(self):
        read_path = self.asset_path + '/map.osm'
        self.buildings = extract_building_info(read_path, save_fig=False)

    def setup(self, experiment_config):
        """Perform the initial experiment setup e.g., loading the map

        Parameters
        ----------
        experiment_config : yaml
            A yaml file providing the map configuration

        Returns
        -------
        None

        Raises
        ------
        FileNotFoundError
            If the requested map cannot be found
        """
        self.experiment_config = experiment_config

        # Read path for the assets
        self.asset_path = get_asset_path(self.experiment_config['map_to_use'])

        # Initialize the assests
        self._affine_transformation_and_graph()
        self._setup_building_info()
        return None

    def get_building_footprints(self):
        """Building outlines in simulator (x, y) coordinates, as a list of (n, 2) arrays."""
        if not hasattr(self, '_footprints'):
            found = extract_building_footprints(self.asset_path + '/map.osm')
            self._footprints = [self._to_cartesian(outline) for outline, _ in found]
            self._footprint_categories = [category for _, category in found]
        return self._footprints

    def get_building_categories(self):
        """Category of each footprint from :meth:`get_building_footprints`, in the same order."""
        self.get_building_footprints()
        return self._footprint_categories

    def get_street_segments(self):
        """Street polylines in simulator (x, y) coordinates, as a list of (n, 2) arrays."""
        if not hasattr(self, '_segments'):
            self._segments = []
            for u, v, data in self.node_graph.edges(data=True):
                if 'geometry' in data:
                    lon, lat = data['geometry'].xy
                else:
                    lon = [self.node_graph.nodes[u]['x'], self.node_graph.nodes[v]['x']]
                    lat = [self.node_graph.nodes[u]['y'], self.node_graph.nodes[v]['y']]
                self._segments.append(self._to_cartesian(np.column_stack([lat, lon])))
        return self._segments

    def _to_cartesian(self, lat_lon):
        padded = np.hstack([np.asarray(lat_lon), np.ones((len(lat_lon), 1))])
        return (padded @ self.A)[:, :2]

    def get_affine_transformation_and_graph(self):
        """Get the transformation matrix and the node graph of the map

        Returns
        -------
        array, node graph
            The transformation matrix and the node graph
        """
        return self.A, self.node_graph

    def get_node_graph(self):
        """Get the node graph of the world

        Returns
        -------
        networkx graph
            A node graph of the world map
        """
        return self.node_graph

    def get_node_info(self, node_index):
        """Get the information about a node.

        Parameters
        ----------
        id : int
            Node ID

        Returns
        -------
        dict
            A dictionary containing all the information about the node.
        """

        return self.node_graph.nodes[node_index]

    def convert_to_lat_lon(self, point):
        """Convert a given point to lat lon co-ordinates

        Parameters
        ----------
        point : array
            A numpy array in pybullet cartesian co-ordinates

        Returns
        -------
        lat_lon : array
            The lat lon co-ordinates
        """
        point[2] = 1
        lat_lon = np.dot(point, np.linalg.inv(self.A))
        return lat_lon

    def convert_to_cartesian(self, point):
        """Convert a lat lon co-ordinates to cartesian coordinates

        Parameters
        ----------
        point : array
            A numpy array in lat lon co-ordinates co-ordinates

        Returns
        -------
        lat_lon : array
            The cartesian coordinates
        """
        return np.dot([point[0], point[1], 1], self.A)

    def get_building_info(self, building_index):
        """Get the information about a building such as perimeter,
        position, number of floors.

        Parameters
        ----------
        id : int
            Building ID

        Returns
        -------
        dict
            A dictionary containing all the information about the building.
        """
        return self.buildings.loc[self.buildings['id'] == building_index]

    def get_lat_lon_spawn_points(self, n_points=5):
        """Get the latitude and longitude spawn points

        Parameters
        ----------
        n_points : int, optional
            Number of points to random latitude and longitude points, by default 5

        Returns
        -------
        array
            An array of cartesian spawn points
        """
        # TODO: Verify if the projection is correct and the warning is not
        # affecting the values
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gdf = ox.utils_geo.sample_points(self.node_graph, n_points)
            points = np.vstack([gdf.centroid.y, gdf.centroid.x]).T
        return points

    def get_cartesian_node_position(self, node_index):
        """Get the cartesian co-ordinates given the node index

        Parameters
        ----------
        node_index : int
            The node index in the map

        Returns
        -------
        array
            The cartesian co-ordinates
        """
        node_info = self.get_node_info(node_index=node_index)
        lat = node_info['y']
        lon = node_info['x']
        cartesian_pos = np.dot([lat, lon, 1], self.A)
        return cartesian_pos

    def get_lat_lon_node_position(self, node_index):
        """Get the lat and lon given the node index

        Parameters
        ----------
        node_index : int
            The node index in the map

        Returns
        -------
        array
            The cartesian co-ordinates
        """
        node_info = self.get_node_info(node_index=node_index)
        lat = node_info['y']
        lon = node_info['x']
        return [lat, lon]

    def get_cartesian_spawn_points(self, n_points=5):
        """Get the cartesian spawn points

        Parameters
        ----------
        n_points : int, optional
            Number of points to random cartesian co-ordinates, by default 5

        Returns
        -------
        array
            An array of cartesian spawn points
        """
        lat_lon_points = self.get_lat_lon_spawn_points(n_points)

        cartesian_spawn_points = []
        for point in lat_lon_points:
            cartesian_spawn_points.append(np.dot([point[0], point[1], 1], self.A))
        return cartesian_spawn_points[0]

    def get_all_buildings(self):
        """Get all the buildings

        Returns
        -------
        dataframe
            A dataframe with all the building information
        """
        return self.buildings

    def get_transformation_matrix(self):
        """Get the transformation matrix to convert lat lon to cartesian

        Returns
        -------
        array
            The transformation matrix
        """
        return self.A
