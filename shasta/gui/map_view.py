import numpy as np
import pygame

BACKGROUND = (22, 25, 30)
BUILDING = (54, 60, 70)
BUILDING_EDGE = (78, 86, 98)
STREET = (112, 120, 134)
NODE = (60, 225, 235)
BUILDING_COLORS = {
    'civic': (128, 98, 190),
    'worship': (190, 92, 150),
    'commercial': (64, 140, 100),
    'residential': (168, 138, 92),
    'industrial': (128, 108, 98),
    'other': BUILDING,
}
BUILDING_LABELS = {
    'civic': 'Civic / public', 'worship': 'Worship', 'commercial': 'Commercial / office',
    'residential': 'Residential', 'industrial': 'Garage / industrial', 'other': 'Other',
}
UAV_COLOR = (80, 150, 255)
UGV_COLOR = (255, 100, 90)
TARGET = (255, 200, 60)
TARGET_DONE = (90, 220, 130)
PENDING = (255, 255, 255)
GROUP_TYPE_COLOR = {'uav': UAV_COLOR, 'ugv': UGV_COLOR}


class MapView:
    """Top-down, north-up view of the map with pan and zoom."""

    def __init__(self, rect, world_map):
        self.rect = pygame.Rect(rect)
        self.map = world_map
        self.footprints = world_map.get_building_footprints()
        self.categories = world_map.get_building_categories()
        self.segments = world_map.get_street_segments()
        graph = world_map.get_node_graph()
        self.node_ids = list(graph.nodes)
        self.node_xy = np.array([world_map.get_cartesian_node_position(n)[:2] for n in self.node_ids])
        self.font = pygame.font.Font(None, 20)
        self.small = pygame.font.Font(None, 16)
        self._cache = None
        self.fit()

    def fit(self):
        points = np.vstack([self.node_xy] + [f for f in self.footprints]) if self.footprints else self.node_xy
        low, high = points.min(axis=0), points.max(axis=0)
        span = np.maximum(high - low, 1.0)
        self.scale = 0.92 * min(self.rect.width / span[0], self.rect.height / span[1])
        self.center = (low + high) / 2

    def to_screen(self, xy):
        xy = np.atleast_2d(xy)
        sx = self.rect.centerx + (xy[:, 0] - self.center[0]) * self.scale
        sy = self.rect.centery - (xy[:, 1] - self.center[1]) * self.scale
        return np.column_stack([sx, sy])

    def to_world(self, sx, sy):
        return np.array([
            self.center[0] + (sx - self.rect.centerx) / self.scale,
            self.center[1] - (sy - self.rect.centery) / self.scale,
        ])

    def zoom_at(self, screen_pos, factor):
        before = self.to_world(*screen_pos)
        self.scale = float(np.clip(self.scale * factor, 0.05, 60.0))
        after = self.to_world(*screen_pos)
        self.center += before - after

    def pan(self, dx, dy):
        self.center -= np.array([dx, -dy]) / self.scale

    def nearest_node(self, screen_pos):
        world = self.to_world(*screen_pos)
        return self.node_ids[int(np.argmin(np.linalg.norm(self.node_xy - world, axis=1)))]

    def _static_layer(self):
        key = (round(self.scale, 4), tuple(np.round(self.center, 2)), self.rect.size)
        if self._cache and self._cache[0] == key:
            return self._cache[1]
        layer = pygame.Surface(self.rect.size)
        layer.fill(BACKGROUND)
        shift = np.array(self.rect.topleft)
        for outline, category in zip(self.footprints, self.categories):
            pts = (self.to_screen(outline) - shift).tolist()
            if len(pts) > 2:
                fill = BUILDING_COLORS[category]
                pygame.draw.polygon(layer, fill, pts)
                pygame.draw.polygon(layer, tuple(min(255, c + 30) for c in fill), pts, 1)
        width = max(1, int(self.scale * 3.0))
        for segment in self.segments:
            pts = (self.to_screen(segment) - shift).tolist()
            if len(pts) > 1:
                pygame.draw.lines(layer, STREET, False, pts, width)
        radius = 2
        for p in (self.to_screen(self.node_xy) - shift):
            pygame.draw.circle(layer, NODE, p.astype(int).tolist(), radius)
        self._cache = (key, layer)
        return layer

    def _label(self, surface, text, pos, color=(230, 230, 235), font=None):
        image = (font or self.font).render(text, True, color)
        surface.blit(image, image.get_rect(center=(int(pos[0]), int(pos[1]))))

    def draw(self, surface, commander, pending_node=None):
        surface.blit(self._static_layer(), self.rect.topleft)
        surface.set_clip(self.rect)
        mission = commander.mission

        if mission:
            for target in mission.targets:
                p = self.to_screen(commander.node_position(target))[0]
                done = target in mission.reached
                color = TARGET_DONE if done else TARGET
                radius = max(8, int(mission.radius * self.scale))
                pygame.draw.circle(surface, color, p.astype(int).tolist(), radius, 2)
                pygame.draw.polygon(surface, color, [(p[0], p[1] - 7), (p[0] + 7, p[1]), (p[0], p[1] + 7), (p[0] - 7, p[1])])
                self._label(surface, f"T{target}", (p[0], p[1] - radius - 9), color, self.small)

        for group_id in commander.groups:
            status = commander.status(group_id)
            color = GROUP_TYPE_COLOR[status['type']]
            path = commander.path(group_id)
            if path is not None and len(path) > 1:
                pts = [tuple(q) for q in self.to_screen(np.vstack([status['centroid'], path]))]
                pygame.draw.lines(surface, color, False, pts, 3 if group_id in commander.selection else 1)
            for xy in self.to_screen(commander.positions[group_id][:, :2]):
                self._draw_vehicle(surface, status['type'], color, xy)
            c = self.to_screen(status['centroid'])[0]
            if group_id in commander.selection:
                width = 3 if group_id == commander.selected else 2
                pygame.draw.circle(surface, PENDING, c.astype(int).tolist(), 16, width)
            self._label(surface, f"{status['type'].upper()} {group_id}", (c[0], c[1] - 24), color)

        if pending_node is not None:
            p = self.to_screen(commander.node_position(pending_node))[0]
            pygame.draw.circle(surface, PENDING, p.astype(int).tolist(), 11, 2)
            pygame.draw.line(surface, PENDING, (p[0] - 16, p[1]), (p[0] + 16, p[1]), 1)
            pygame.draw.line(surface, PENDING, (p[0], p[1] - 16), (p[0], p[1] + 16), 1)
            self._label(surface, f"node {pending_node}", (p[0], p[1] + 24))

        self._draw_legend(surface)
        self._draw_scale_and_compass(surface)
        surface.set_clip(None)

    def _draw_legend(self, surface):
        present = [c for c in BUILDING_COLORS if c in set(self.categories)]
        entries = [(BUILDING_COLORS[c], BUILDING_LABELS[c], 'box') for c in present]
        entries += [(UAV_COLOR, 'UAV', 'tri'), (UGV_COLOR, 'UGV', 'box'), (NODE, 'Street node', 'dot')]
        x, y = self.rect.left + 12, self.rect.top + 52
        panel = pygame.Rect(x - 6, y - 6, 176, 20 * len(entries) + 8)
        backdrop = pygame.Surface(panel.size, pygame.SRCALPHA)
        backdrop.fill((18, 20, 26, 200))
        surface.blit(backdrop, panel.topleft)
        for color, label, shape in entries:
            if shape == 'tri':
                pygame.draw.polygon(surface, color, [(x + 7, y + 1), (x + 14, y + 14), (x, y + 14)])
            elif shape == 'box':
                pygame.draw.rect(surface, color, (x, y + 2, 14, 12))
            else:
                pygame.draw.circle(surface, color, (x + 7, y + 8), 3)
            image = self.small.render(label, True, (215, 218, 226))
            surface.blit(image, (x + 22, y + 3))
            y += 20

    def _draw_vehicle(self, surface, kind, color, xy, size=7):
        x, y = float(xy[0]), float(xy[1])
        if kind == 'uav':
            points = [(x, y - size - 1), (x + size, y + size - 2), (x - size, y + size - 2)]
        else:
            points = [(x - size + 1, y - size + 1), (x + size - 1, y - size + 1),
                      (x + size - 1, y + size - 1), (x - size + 1, y + size - 1)]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (10, 10, 14), points, 2)

    def _draw_scale_and_compass(self, surface):
        target_px = 120
        meters = target_px / self.scale
        nice = min((v for v in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if v >= meters * 0.6), default=1000)
        x0, y0 = self.rect.left + 16, self.rect.bottom - 18
        length = nice * self.scale
        pygame.draw.line(surface, (220, 220, 225), (x0, y0), (x0 + length, y0), 2)
        self._label(surface, f"{nice} m", (x0 + length / 2, y0 - 10), (220, 220, 225), self.small)
        cx, cy = self.rect.right - 34, self.rect.top + 44
        pygame.draw.polygon(surface, (220, 220, 225), [(cx, cy - 20), (cx - 7, cy + 8), (cx + 7, cy + 8)], 1)
        self._label(surface, "N", (cx, cy - 30), (220, 220, 225))
