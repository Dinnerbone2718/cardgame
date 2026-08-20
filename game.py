import math
import pygame
import controller
from units import spawn_unit
from effects import Trigger


DEFAULT_ENEMY_TEAM = ["demon", "demon", "demon", "demon"]

OUTCOME_DISPLAY_DURATION = 1.8


class Game:
    def __init__(self, screen, enemy_team_names=None, player_state=None, on_win=None, on_loss=None):
        self.screen = screen

        self.on_win = on_win
        self.on_loss = on_loss
        self.outcome = None
        self.outcome_timer = 0.0
        self._outcome_triggered = False

        self.turn = "player"

        self.player = controller.Controller(self, True)
        self.enemy = controller.Controller(self, False)

        if player_state is not None:
            self.player_team = player_state.build_team()
        else:
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
            unit.update(clock, self)

        dt = clock.get_time() / 1000

        if self.outcome is None:
            self.player.update(dt)
            self.enemy.update(dt)
            self.check_outcome()
        else:
            self.outcome_timer += dt
            if not self._outcome_triggered and self.outcome_timer >= OUTCOME_DISPLAY_DURATION:
                self._outcome_triggered = True
                callback = self.on_win if self.outcome == "win" else self.on_loss
                if callback is not None:
                    callback()

        for effect in self.visual_effects:
            effect.update(dt)
        self.visual_effects = [e for e in self.visual_effects if not e.finished]

    def check_outcome(self):
        if self.outcome is not None:
            return

        if self.enemy_team and all(unit.is_dead for unit in self.enemy_team):
            self.outcome = "win"
            self.outcome_timer = 0.0
            return

        if self.player_team and all(unit.is_dead for unit in self.player_team):
            self.outcome = "loss"
            self.outcome_timer = 0.0
            return

        alive_player = [unit for unit in self.player_team if not unit.is_dead]
        if alive_player and not any(
            any(card.can_play(self, unit) for card in unit.hand)
            for unit in alive_player
        ):
            self.outcome = "loss"
            self.outcome_timer = 0.0

    def handle_keydown(self, key):
        if self.outcome is not None:
            return
        self.player.handle_keydown(key)

    def handle_mousedown(self, pos):
        if self.outcome is not None:
            return
        self.player.handle_mousedown(pos)

    def handle_mouseup(self, pos):
        if self.outcome is not None:
            return
        self.player.handle_mouseup(pos)

    def end_turn(self):
        self.turn = "enemy" if self.turn == "player" else "player"

        team = self.player_team if self.turn == "player" else self.enemy_team
        for unit in team:
            unit.tick_statuses(self)
            unit.trigger_passives(self, Trigger.ON_TURN_START)

    def draw(self):
        self.screen.draw()
        self.draw_units()
        self.draw_visual_effects()

        self.player.draw()
        self.enemy.draw()

        if self.outcome is not None:
            self._draw_outcome_overlay()

    def _draw_outcome_overlay(self):
        surface = self.screen.get_surface()
        width = self.screen.width
        height = self.screen.height

        fade_t = min(1.0, self.outcome_timer / 0.4)
        ease = 1 - (1 - fade_t) ** 3

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(140 * ease)))
        surface.blit(overlay, (0, 0))

        if self.outcome == "win":
            label = "VICTORY"
            color = (110, 220, 130)
        else:
            label = "DEFEAT"
            color = (220, 90, 90)

        font_size = int(height * 0.12 * (0.7 + 0.3 * ease))
        font = pygame.font.SysFont("comicsansms", max(1, font_size), bold=True)

        wobble = math.sin(self.outcome_timer * 6) * 4 * (1 - ease)
        text = font.render(label, True, color)
        rect = text.get_rect(center=(width // 2, int(height * 0.4) + int(wobble)))

        outline = font.render(label, True, (0, 0, 0))
        for ox, oy in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            outline_rect = outline.get_rect(center=(rect.centerx + ox, rect.centery + oy))
            surface.blit(outline, outline_rect)
        surface.blit(text, rect)

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