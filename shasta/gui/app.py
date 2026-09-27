import numpy as np
import pygame
import pygame_gui

from .map_view import GROUP_TYPE_COLOR, MapView

SIDE_WIDTH = 400
SPEEDS = (1, 2, 4, 8)
HELP = (
    "Click node: target  |  Enter: send  |  Shift+click / Shift+drag: multi-select  |  wheel: zoom  |  right-drag: pan",
    "U / G / Ctrl+A: all UAV / UGV / groups  |  1-9: group  |  Space: pause  |  +/-: speed  |  V: 3D view  |  R: reset view",
)


def _hex(color):
    return "#%02x%02x%02x" % tuple(color)


class CameraInset:
    """Small pybullet camera image that follows the selected group."""

    size = (320, 240)

    def __init__(self, physics_client):
        self.client = physics_client
        self.surface = None
        self.projection = physics_client.computeProjectionMatrixFOV(60, self.size[0] / self.size[1], 0.5, 2000)

    def refresh(self, centroid, yaw):
        view = self.client.computeViewMatrixFromYawPitchRoll(
            [float(centroid[0]), float(centroid[1]), 5.0], 90.0, yaw, -55.0, 0, 2
        )
        width, height, rgba, *_ = self.client.getCameraImage(
            *self.size, viewMatrix=view, projectionMatrix=self.projection,
            renderer=self.client.ER_TINY_RENDERER,
        )
        array = np.reshape(np.asarray(rgba, dtype=np.uint8), (height, width, 4))[:, :, :3]
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))


class ShastaGUI:
    """Human interface: watch the swarm on the map and command groups."""

    def __init__(self, commander, size=(1280, 800)):
        pygame.init()
        pygame.display.set_caption("SHASTA - human-swarm teaming")
        self.screen = pygame.display.set_mode(size)
        self.size = size
        self.commander = commander
        self.map_rect = pygame.Rect(0, 0, size[0] - SIDE_WIDTH, size[1])
        self.view = MapView(self.map_rect, commander.map)
        self.manager = pygame_gui.UIManager(size)
        self.manager.preload_fonts(
            [{'name': 'noto_sans', 'point_size': 14, 'style': style, 'antialiased': '1'}
             for style in ('bold',)]
        )
        self.clock = pygame.time.Clock()
        self.pending = None
        self.speed_index = 0
        self.running = True
        self.dragging = False
        self.box_start = None
        self.box_end = None
        self.last_click = (0, None)
        self.camera = None
        self.show_camera = False
        self.frame = 0
        self._texts = {}
        self._build_panel()
        self._apply_speed()
        self._refresh_text(force=True)

    # ---- layout -----------------------------------------------------------------
    def _build_panel(self):
        x0 = self.size[0] - SIDE_WIDTH + 12
        w = SIDE_WIDTH - 24
        m = self.manager
        rect = pygame.Rect
        self.mission_box = pygame_gui.elements.UITextBox("", rect(x0, 10, w, 84), m)
        y = 104
        third = (w - 12) // 3
        self.all_uav_button = pygame_gui.elements.UIButton(rect(x0, y, third, 30), "All UAV (U)", m)
        self.all_ugv_button = pygame_gui.elements.UIButton(rect(x0 + third + 6, y, third, 30), "All UGV (G)", m)
        self.all_groups_button = pygame_gui.elements.UIButton(rect(x0 + 2 * (third + 6), y, third, 30), "All (Ctrl+A)", m)
        y += 38
        self.detail_box = pygame_gui.elements.UITextBox("", rect(x0, y, w, 184), m)
        y += 192
        half = (w - 6) // 2
        self.send_button = pygame_gui.elements.UIButton(rect(x0, y, half, 36), "Send order (Enter)", m)
        self.cancel_button = pygame_gui.elements.UIButton(rect(x0 + half + 6, y, half, 36), "Cancel order", m)
        y += 42
        self.all_button = pygame_gui.elements.UIButton(rect(x0, y, half, 36), "Send ALL groups", m)
        self.pause_button = pygame_gui.elements.UIButton(rect(x0 + half + 6, y, half, 36), "Pause (Space)", m)
        y += 42
        self.slower_button = pygame_gui.elements.UIButton(rect(x0, y, 48, 32), "-", m)
        self.speed_label = pygame_gui.elements.UILabel(rect(x0 + 52, y, w - 104, 32), "", m)
        self.faster_button = pygame_gui.elements.UIButton(rect(x0 + w - 48, y, 48, 32), "+", m)
        y += 40
        self.log_box = pygame_gui.elements.UITextBox("", rect(x0, y, w, self.size[1] - y - 10), m)
        self.actions = {
            self.send_button: self.send_pending,
            self.cancel_button: self.commander.cancel_selected,
            self.all_uav_button: lambda: self.select_type('uav'),
            self.all_ugv_button: lambda: self.select_type('ugv'),
            self.all_groups_button: lambda: self.select_type(None),
            self.all_button: self.send_all_pending,
            self.pause_button: self.toggle_pause,
            self.slower_button: lambda: self._change_speed(-1),
            self.faster_button: lambda: self._change_speed(1),
        }

    # ---- commands ---------------------------------------------------------------
    def _shift(self):
        return bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)

    def select_group(self, group_id, add=False):
        self.commander.select(group_id, add=add)
        self._refresh_text(force=True)

    def select_type(self, kind):
        self.commander.select_type(kind)
        self._refresh_text(force=True)

    def send_pending(self):
        if self.pending is None:
            self.commander.log("Pick a target node on the map first")
        else:
            self.commander.send_selected(self.pending)

    def send_all_pending(self):
        if self.pending is None:
            self.commander.log("Pick a target node on the map first")
        else:
            self.commander.send_all(self.pending)

    def toggle_pause(self):
        self.commander.toggle_pause()

    def _change_speed(self, delta):
        self.speed_index = int(np.clip(self.speed_index + delta, 0, len(SPEEDS) - 1))
        self._apply_speed()

    def _apply_speed(self):
        self.commander.steps_per_update = 4 * SPEEDS[self.speed_index]
        self.speed_label.set_text(f"Speed x{SPEEDS[self.speed_index]}")

    def toggle_camera(self):
        self.show_camera = not self.show_camera
        if self.show_camera and self.camera is None:
            self.camera = CameraInset(self.commander.env.core.get_physics_client())

    # ---- input ------------------------------------------------------------------
    def _marker_hit(self, pos):
        best, best_dist = None, 20
        for group_id in self.commander.groups:
            c = self.view.to_screen(self.commander.status(group_id)['centroid'])[0]
            dist = float(np.hypot(c[0] - pos[0], c[1] - pos[1]))
            if dist < best_dist:
                best, best_dist = group_id, dist
        return best

    def _map_click(self, pos):
        hit = self._marker_hit(pos)
        if hit is not None:
            self.select_group(hit, add=self._shift())
            return
        if self._shift():
            self.box_start = self.box_end = pos
            return
        node = self.view.nearest_node(pos)
        now = pygame.time.get_ticks()
        if node == self.last_click[1] and now - self.last_click[0] < 400:
            self.pending = node
            self.send_pending()
        self.pending = node
        self.last_click = (now, node)

    def _finish_box(self, end):
        box = pygame.Rect(self.box_start, (end[0] - self.box_start[0], end[1] - self.box_start[1]))
        box.normalize()
        self.box_start = self.box_end = None
        if box.width < 6 and box.height < 6:
            return
        inside = [
            group_id for group_id in self.commander.groups
            if box.collidepoint(self.view.to_screen(self.commander.status(group_id)['centroid'])[0])
        ]
        if inside:
            self.commander.select_many(inside, add=self._shift())
            self._refresh_text(force=True)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            groups = list(self.commander.groups)
            if event.key == pygame.K_ESCAPE:
                self.pending = None
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.send_pending()
            elif event.key == pygame.K_SPACE:
                self.toggle_pause()
            elif event.key == pygame.K_u:
                self.select_type('uav')
            elif event.key == pygame.K_g:
                self.select_type('ugv')
            elif event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                self.select_type(None)
            elif event.key == pygame.K_v:
                self.toggle_camera()
            elif event.key == pygame.K_r:
                self.view.fit()
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self._change_speed(1)
            elif event.key == pygame.K_MINUS:
                self._change_speed(-1)
            elif pygame.K_1 <= event.key <= pygame.K_9:
                index = event.key - pygame.K_1
                if index < len(groups):
                    self.select_group(groups[index], add=bool(event.mod & pygame.KMOD_SHIFT))
        elif event.type == pygame.MOUSEBUTTONDOWN and self.map_rect.collidepoint(event.pos):
            if event.button == 1:
                self._map_click(event.pos)
            elif event.button == 3:
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.dragging = False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.box_start:
            self._finish_box(event.pos)
        elif event.type == pygame.MOUSEMOTION and self.box_start:
            self.box_end = event.pos
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.view.pan(*event.rel)
        elif event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.map_rect.collidepoint(pos):
                self.view.zoom_at(pos, 1.15 ** event.y)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            action = self.actions.get(event.ui_element)
            if action:
                action()
        self.manager.process_events(event)

    # ---- drawing ----------------------------------------------------------------
    def _set_text(self, key, element, html):
        if self._texts.get(key) != html:
            self._texts[key] = html
            element.set_text(html)

    def _refresh_text(self, force=False):
        if not force and self.frame % 6:
            return
        c = self.commander
        mission = c.mission
        lines = [f"<b>Time</b> {c.step_count} steps" + ("  <b>(PAUSED)</b>" if c.paused else "")]
        if mission:
            lines.append(f"<b>Targets</b> {mission.score}/{len(mission.targets)} reached")
            if mission.time_limit:
                lines.append(f"<b>Time left</b> {max(0, mission.time_limit - c.step_count)}")
            if mission.is_complete():
                lines.append("<b><font color=#5ee08a>MISSION COMPLETE</font></b>")
            elif mission.is_over(c.step_count):
                lines.append("<b><font color=#ff7070>TIME UP</font></b>")
        self._set_text('mission', self.mission_box, "<br>".join(lines))

        pending = "none" if self.pending is None else f"node {self.pending}"
        if len(c.selection) == 1:
            s = c.status(c.selected)
            color = _hex(GROUP_TYPE_COLOR[s['type']])
            target = "no order" if s['target'] is None else f"node {s['target']}"
            detail = [
                f"<b><font color={color}>{s['type'].upper()} group {s['group']}</font></b> ({s['size']} vehicles)",
                f"Position ({s['centroid'][0]:.0f}, {s['centroid'][1]:.0f}) m",
                f"Battery {s['battery']:.0f}%   Ammo {s['ammo']:.0f}%",
                f"Order: {target}" + ("  (arrived)" if s['arrived'] else ""),
            ]
            if s['distance'] is not None and not s['arrived']:
                detail.append(f"Distance {s['distance']:.0f} m, ETA {s['eta']:.0f} steps")
        else:
            statuses = [c.status(g) for g in c.selection]
            names = ", ".join(f"{t['type'].upper()} {t['group']}" for t in statuses[:6])
            if len(statuses) > 6:
                names += f" +{len(statuses) - 6} more"
            vehicles = sum(t['size'] for t in statuses)
            detail = [
                f"<b>{len(statuses)} groups selected</b> ({vehicles} vehicles)",
                names,
                f"Avg battery {np.mean([t['battery'] for t in statuses]):.0f}%",
                f"With orders: {sum(t['target'] is not None for t in statuses)}/{len(statuses)}",
                f"Arrived: {sum(t['arrived'] for t in statuses)}/{len(statuses)}",
            ]
        detail.append(f"Pending target: {pending}")
        self._set_text('detail', self.detail_box, "<br>".join(detail))

        log = [f"[{t}] {text}" for t, text in reversed(c.events[-14:])]
        self._set_text('log', self.log_box, "<br>".join(log) if log else "Events appear here.")

        self.pause_button.set_text("Resume (Space)" if c.paused else "Pause (Space)")

    def draw(self):
        self.screen.fill((22, 25, 30))
        self.view.draw(self.screen, self.commander, self.pending)
        font = pygame.font.Font(None, 18)
        for i, line in enumerate(HELP):
            self.screen.blit(font.render(line, True, (170, 176, 188)), (12, 8 + 16 * i))
        if self.show_camera and self.camera:
            if self.frame % 10 == 0:
                centroid = self.commander.status(self.commander.selected)['centroid']
                self.camera.refresh(centroid, yaw=0.0)
            if self.camera.surface:
                x, y = 12, self.map_rect.bottom - self.camera.size[1] - 40
                self.screen.blit(self.camera.surface, (x, y))
                pygame.draw.rect(self.screen, (220, 220, 225), (x, y, *self.camera.size), 1)
        self.manager.draw_ui(self.screen)
        if self.box_start and self.box_end:
            box = pygame.Rect(self.box_start, (self.box_end[0] - self.box_start[0], self.box_end[1] - self.box_start[1]))
            box.normalize()
            fill = pygame.Surface(box.size, pygame.SRCALPHA)
            fill.fill((255, 255, 255, 30))
            self.screen.blit(fill, box.topleft)
            pygame.draw.rect(self.screen, (255, 255, 255), box, 1)

    # ---- main loop --------------------------------------------------------------
    def step(self, dt=1 / 30):
        for event in pygame.event.get():
            self.handle_event(event)
        self.commander.update()
        self.manager.update(dt)
        self._refresh_text()
        self.draw()
        pygame.display.flip()
        self.frame += 1

    def run(self, max_frames=None):
        while self.running and (max_frames is None or self.frame < max_frames):
            self.step(self.clock.tick(30) / 1000)
        pygame.quit()
