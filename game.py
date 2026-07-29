import pygame
import controller
from units import spawn_unit
from effects import Trigger


DEFAULT_ENEMY_TEAM = ["demon", "demon", "demon", "demon"]


class Game:
    def __init__(self, screen, enemy_team_names=None):
        self.screen = screen

        self.turn = "player"

        self.player = controller.Controller(self, True)
        self.enemy = controller.Controller(self, False)

        self.player_team = [
            spawn_unit("blob"),
            spawn_unit("frog"),
            spawn_unit("penguin"),
            spawn_unit("spacecat"),
        ]

        if enemy_team_names is None:
            enemy_team_names = DEFAULT_ENEMY_TEAM
        self.enemy_team = [spawn_unit(name) for name in enemy_team_names]

        self._unit_rects = {}
        self.visual_effects = []



    def update(self, clock):
        for unit in self.player_team + self.enemy_team:
            unit.update(clock)

        dt = clock.get_time() / 1000
        self.player.update(dt)
        self.enemy.update(dt)

        for effect in self.visual_effects:
            effect.update(dt)
        self.visual_effects = [e for e in self.visual_effects if not e.finished]

    def handle_keydown(self, key):
        self.player.handle_keydown(key)

    def handle_mousedown(self, pos):
        self.player.handle_mousedown(pos)

    def handle_mouseup(self, pos):
        self.player.handle_mouseup(pos)

    def end_turn(self):
        self.turn = "enemy" if self.turn == "player" else "player"

        team = self.player_team if self.turn == "player" else self.enemy_team
        for unit in team:
            unit.trigger_passives(self, Trigger.ON_TURN_START)

    def draw(self):
        self.screen.draw()
        self.draw_units()
        self.draw_visual_effects()

        self.player.draw()
        self.enemy.draw()

    def draw_visual_effects(self):
        surface = self.screen.get_surface()
        for effect in self.visual_effects:
            effect.draw(surface)


    def draw_units(self):
        surface = self.screen.get_surface()
        width = self.screen.width
        height = self.screen.height
        unit_size = height // 5

        self._draw_team(surface, self.player_team, width // 5, height, unit_size, True)
        self._draw_team(surface, self.enemy_team, (4 * width) // 5, height, unit_size, False)

    def _draw_team(self, surface, team, x, height, unit_size, left):
        if not team:
            return
        spacing = height / (len(team) + 1)
        for i, unit in enumerate(team):
            y = int(spacing * (i + 1))
            unit.draw(surface, x, y, unit_size, left)
            rect = pygame.Rect(0, 0, unit_size, unit_size)
            rect.center = (x, y)
            self._unit_rects[unit] = rect

    def get_unit_rect(self, unit):
        return self._unit_rects.get(unit)

    def get_unit_at(self, pos):
        for unit, rect in self._unit_rects.items():
            if unit.is_dead:
                continue
            if rect.collidepoint(pos):
                return unit
        return None