"""Interact with SHaSTA's PyBullet world, in 3D, in the browser.

PyBullet is the physics engine under SHaSTA, and it runs with no window at all. It can still render the scene to an image
(``getCameraImage``), so this view draws the 3D world, lets you move the camera with the mouse, and turns a click on the ground into
an order for the selected group. Use it with ``play_world(commander)``.

    left-drag: orbit      right-drag: pan      wheel: zoom      click the ground: send the selected group there
    1-9: pick a group     Space: pause         + / -: speed     F: follow the selected group     R: reset the camera
"""
import time

import numpy as np
import pygame

from live_play import play_live

COLORS = {"uav": (80, 160, 255), "ugv": (255, 90, 90)}


class WorldView:
    def __init__(self, commander, size=(800, 500), scale=0.6, draw_fps=10):
        # PyBullet draws the scene on the CPU, which is the slow part. It draws a smaller picture (``scale``) that is then enlarged,
        # and only ``draw_fps`` times a second: the simulation keeps its pace in between.
        self.commander, self.size, self.scale, self.draw_fps = commander, size, scale, draw_fps
        self.render_size = (max(80, int(size[0] * scale)), max(50, int(size[1] * scale)))
        self.client = commander.env.core.get_physics_client()
        self.projection = self.client.computeProjectionMatrixFOV(60, size[0] / size[1], 0.5, 3000)
        self.nodes = {n: commander.map.get_cartesian_node_position(n)[:2] for n in commander.map.get_node_graph().nodes}
        self.reset_camera()
        self.follow, self.pick, self.down = True, None, None

    def reset_camera(self):
        self.yaw, self.pitch, self.distance = 30.0, -50.0, 170.0
        self.target = np.array(self.commander.status(self.commander.selected)["centroid"][:2], dtype=float)

    # ---- the camera -------------------------------------------------------------------------------------------------
    def _view(self):
        return self.client.computeViewMatrixFromYawPitchRoll([float(self.target[0]), float(self.target[1]), 0.0], self.distance,
                                                             self.yaw, self.pitch, 0, 2)

    def project(self, xyz, view):
        """World position (metres) -> pixel on the picture, or None when it is behind the camera."""
        clip = (np.array(self.projection).reshape(4, 4, order="F") @ np.array(view).reshape(4, 4, order="F")) @ np.append(xyz, 1.0)
        if clip[3] <= 0:
            return None
        return int((clip[0] / clip[3] + 1) / 2 * self.size[0]), int((1 - clip[1] / clip[3]) / 2 * self.size[1])

    def ground_point(self, pixel, view):
        """The point on the ground (z = 0) under a pixel: the ray through the pixel, intersected with the ground."""
        inverse = np.linalg.inv(np.array(self.projection).reshape(4, 4, order="F") @ np.array(view).reshape(4, 4, order="F"))
        near, far = (inverse @ np.array([2 * pixel[0] / self.size[0] - 1, 1 - 2 * pixel[1] / self.size[1], z, 1.0]) for z in (-1.0, 1.0))
        near, far = near[:3] / near[3] if near[3] else near[:3], far[:3] / far[3] if far[3] else far[:3]
        if abs(far[2] - near[2]) < 1e-9:
            return None
        return (near + (far - near) * (-near[2] / (far[2] - near[2])))[:2]

    # ---- input ------------------------------------------------------------------------------------------------------
    def _click(self, pixel, view):
        ground = self.ground_point(pixel, view)
        if ground is None:
            return
        node = min(self.nodes, key=lambda n: np.linalg.norm(self.nodes[n] - ground))
        self.pick = node
        self.commander.send(self.commander.selected, node)

    def handle(self, event, view):
        c = self.commander
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.down = (event.pos, event.button)
        elif event.type == pygame.MOUSEBUTTONUP and self.down:
            (x, y), button = self.down
            if button == 1 and abs(event.pos[0] - x) + abs(event.pos[1] - y) < 6:
                self._click(event.pos, view)
            self.down = None
        elif event.type == pygame.MOUSEMOTION and self.down:
            dx, dy = event.rel
            if self.down[1] == 1:
                self.yaw, self.pitch = self.yaw - 0.4 * dx, float(np.clip(self.pitch - 0.3 * dy, -89, -10))
            elif self.down[1] == 3:
                self.follow = False
                angle, scale = np.radians(self.yaw), self.distance / 600
                self.target += scale * np.array([-dx * np.cos(angle) + dy * np.sin(angle), dx * np.sin(angle) + dy * np.cos(angle)])
        elif event.type == pygame.MOUSEWHEEL:
            self.distance = float(np.clip(self.distance * 1.15 ** -event.y, 20, 1500))
        elif event.type == pygame.KEYDOWN:
            groups = list(c.groups)
            if event.key == pygame.K_SPACE:
                c.toggle_pause()
            elif event.key == pygame.K_f:
                self.follow = not self.follow
            elif event.key == pygame.K_r:
                self.reset_camera(); self.follow = True
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                c.steps_per_update = min(64, c.steps_per_update * 2)
            elif event.key == pygame.K_MINUS:
                c.steps_per_update = max(1, c.steps_per_update // 2)
            elif pygame.K_1 <= event.key <= pygame.K_9 and event.key - pygame.K_1 < len(groups):
                c.select(groups[event.key - pygame.K_1])

    # ---- drawing ----------------------------------------------------------------------------------------------------
    def draw(self, screen, view, font):
        c = self.commander
        width, height, rgba, *_ = self.client.getCameraImage(*self.render_size, viewMatrix=view, projectionMatrix=self.projection,
                                                            renderer=self.client.ER_TINY_RENDERER)
        picture = np.reshape(np.asarray(rgba, dtype=np.uint8), (height, width, 4))[:, :, :3]
        picture = pygame.surfarray.make_surface(picture.swapaxes(0, 1))
        screen.blit(pygame.transform.smoothscale(picture, self.size) if self.scale < 1 else picture, (0, 0))
        for target in (c.mission.targets if c.mission else []):                   # the mission's targets
            spot = self.project(np.append(self.nodes[target], 0.0), view)
            if spot:
                pygame.draw.circle(screen, (255, 215, 0), spot, 11, 2)
        if self.pick is not None and (spot := self.project(np.append(self.nodes[self.pick], 0.0), view)):
            pygame.draw.line(screen, (255, 255, 255), (spot[0] - 7, spot[1]), (spot[0] + 7, spot[1]), 2)
            pygame.draw.line(screen, (255, 255, 255), (spot[0], spot[1] - 7), (spot[0], spot[1] + 7), 2)
        for group_id in c.groups:                                                 # the groups, and their orders
            status = c.status(group_id)
            spot = self.project(np.append(status["centroid"][:2], 6.0), view)
            if spot is None:
                continue
            color = COLORS[status["type"]]
            if group_id in c.orders and not status["arrived"]:
                goal = self.project(np.append(self.nodes[c.orders[group_id]], 0.0), view)
                if goal:
                    pygame.draw.line(screen, color, spot, goal, 1)
            pygame.draw.circle(screen, color, spot, 9, 0 if group_id in c.selection else 2)
            screen.blit(font.render(str(group_id + 1), True, (255, 255, 255)), (spot[0] + 11, spot[1] - 7))
        selected = c.status(c.selected)
        text = (f"group {c.selected + 1} ({selected['type'].upper()}) selected   targets {c.mission.score}/{len(c.mission.targets)}"
                f"   step {c.step_count}" + ("   PAUSED" if c.paused else "")) if c.mission else f"step {c.step_count}"
        screen.blit(font.render(text, True, (255, 255, 255), (0, 0, 0)), (8, 8))
        screen.blit(font.render("left-drag orbit | right-drag pan | wheel zoom | click the ground to send | 1-9 group | Space pause | F follow",
                                True, (200, 200, 205), (0, 0, 0)), (8, self.size[1] - 22))

    def run(self):
        pygame.init()
        screen, clock = pygame.display.set_mode(self.size), pygame.time.Clock()
        font = pygame.font.Font(None, 20)
        last_draw = 0.0
        while True:
            view = self._view()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                self.handle(event, view)
            self.commander.update()
            if self.follow:
                self.target = np.array(self.commander.status(self.commander.selected)["centroid"][:2], dtype=float)
            if time.perf_counter() - last_draw >= 1 / self.draw_fps:           # draw a few times a second, not every update
                self.draw(screen, self._view(), font)
                pygame.display.flip()
                last_draw = time.perf_counter()
            clock.tick(30)


def play_world(commander, fps=10, quality=70, width=800, scale=0.6):
    """Show SHaSTA's PyBullet world in 3D in this cell. Click the picture first."""
    def score():
        mission = commander.mission
        return f"targets reached {mission.score} of {len(mission.targets)}, {commander.step_count} steps" if mission else ""
    play_live(WorldView(commander, scale=scale, draw_fps=fps).run, fps=fps, quality=quality, width=width, summary=score,
              hint="Click the picture, then drag to look around and click the ground to send the selected group.")
