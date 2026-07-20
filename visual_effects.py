import math
import random
import pygame


_image_cache = {}


def _load_image(path):
    if path not in _image_cache:
        _image_cache[path] = pygame.image.load(path).convert_alpha()
    return _image_cache[path]


class CardVisualEffect:

    def __init__(self, duration):
        self.duration = duration
        self.elapsed = 0.0

    @property
    def finished(self):
        return self.elapsed >= self.duration

    def update(self, dt):
        self.elapsed += dt

    def draw(self, surface):
        pass


class ProjectileEffect(CardVisualEffect):
    def __init__(self, game, image_path, source_unit, target_unit,
                 duration=0.4, size=140, spin_speed=1440,
                 impact_text="BOOM!", impact_hold=0.35, trail_length=6):
        super().__init__(duration + impact_hold)
        self.game = game
        self.image = _load_image(image_path)
        self.fly_duration = duration
        self.impact_hold = impact_hold
        self.size = size
        self.spin_speed = spin_speed
        self.impact_text = impact_text

        self.start_pos = self._unit_pos(source_unit, fallback=(0, 0))
        self.end_pos = self._unit_pos(target_unit, fallback=self.start_pos)

        self.trail_length = trail_length
        self._positions = []

    def _unit_pos(self, unit, fallback):
        rect = self.game.get_unit_rect(unit)
        return rect.center if rect else fallback

    def update(self, dt):
        super().update(dt)
        if self.elapsed <= self.fly_duration:
            self._positions.append(self._current_pos())
            if len(self._positions) > self.trail_length:
                self._positions.pop(0)

    def _current_pos(self):
        t = min(1.0, self.elapsed / self.fly_duration) if self.fly_duration > 0 else 1.0
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t
        y += math.sin(t * math.pi * 6) * 10
        return x, y

    def draw(self, surface):
        if self.elapsed <= self.fly_duration:
            self._draw_flight(surface)
        else:
            self._draw_impact(surface)

    def _draw_flight(self, surface):
        count = max(1, len(self._positions))
        angle = self.elapsed * self.spin_speed
        for i, pos in enumerate(self._positions):
            fade = int(255 * (i + 1) / count)
            size = int(self.size * (0.5 + 0.5 * (i + 1) / count))
            img = pygame.transform.smoothscale(self.image, (max(1, size), max(1, size)))
            img = pygame.transform.rotate(img, angle)
            img.set_alpha(fade)
            rect = img.get_rect(center=pos)
            surface.blit(img, rect)

    def _draw_impact(self, surface):
        t = (self.elapsed - self.fly_duration) / self.impact_hold if self.impact_hold else 1.0
        t = min(1.0, max(0.0, t))
        wobble = 1 + 0.4 * math.sin(t * math.pi * 10)
        size = int(self.size * 1.6 * wobble)
        img = pygame.transform.smoothscale(self.image, (max(1, size), max(1, size)))
        rect = img.get_rect(center=self.end_pos)
        surface.blit(img, rect)

        if self.impact_text:
            font = pygame.font.SysFont("comicsansms", int(48 * wobble), bold=True)
            color = (255, random.randint(0, 80), 0)
            text_surf = font.render(self.impact_text, True, color)
            jitter = (random.randint(-4, 4), random.randint(-4, 4))
            text_rect = text_surf.get_rect(
                center=(self.end_pos[0] + jitter[0], self.end_pos[1] - 60 + jitter[1])
            )
            outline = font.render(self.impact_text, True, (0, 0, 0))
            for ox, oy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
                outline_rect = outline.get_rect(center=(text_rect.centerx + ox, text_rect.centery + oy))
                surface.blit(outline, outline_rect)
            surface.blit(text_surf, text_rect)


CARD_VISUAL_EFFECTS = {
    "explosion": lambda game, source, target: ProjectileEffect(
        game, "assets/fireball.png", source, target,
        duration=0.7, size=140, spin_speed=0, impact_text="KABLOEYY",
    ),

    "lazer": lambda game, source, target: ProjectileEffect(
        game, "assets/lazer.png", source, target,
        duration=.5, size=140, spin_speed=0, impact_text="ZZZZ", impact_hold=.4, trail_length=20
    ),

}


def spawn_card_effect(game, card_name, source_unit, target_unit):
    factory = CARD_VISUAL_EFFECTS.get(card_name)
    if factory is None:
        return

    effect = factory(game, source_unit, target_unit)
    if effect is None:
        return

    if isinstance(effect, list):
        game.visual_effects.extend(effect)
    else:
        game.visual_effects.append(effect)