import math
import random
import pygame
import global_value
from effects import Trigger



REFERENCE_HEIGHT = global_value.Global.SCREEN_HEIGHT


def _scale(game):
    return game.screen.height / REFERENCE_HEIGHT


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
        scale = _scale(self.game)
        count = max(1, len(self._positions))
        angle = self.elapsed * self.spin_speed
        for i, pos in enumerate(self._positions):
            fade = int(255 * (i + 1) / count)
            size = int(self.size * scale * (0.5 + 0.5 * (i + 1) / count))
            img = pygame.transform.smoothscale(self.image, (max(1, size), max(1, size)))
            img = pygame.transform.rotate(img, angle)
            img.set_alpha(fade)
            rect = img.get_rect(center=pos)
            surface.blit(img, rect)

    def _draw_impact(self, surface):
        scale = _scale(self.game)
        t = (self.elapsed - self.fly_duration) / self.impact_hold if self.impact_hold else 1.0
        t = min(1.0, max(0.0, t))
        wobble = 1 + 0.4 * math.sin(t * math.pi * 10)
        size = int(self.size * scale * 1.6 * wobble)
        img = pygame.transform.smoothscale(self.image, (max(1, size), max(1, size)))
        rect = img.get_rect(center=self.end_pos)
        surface.blit(img, rect)

        if self.impact_text:
            font = pygame.font.SysFont("comicsansms", max(1, int(48 * scale * wobble)), bold=True)
            color = (255, random.randint(0, 80), 0)
            text_surf = font.render(self.impact_text, True, color)
            jitter = (random.randint(-4, 4) * scale, random.randint(-4, 4) * scale)
            text_rect = text_surf.get_rect(
                center=(self.end_pos[0] + jitter[0], self.end_pos[1] - 60 * scale + jitter[1])
            )
            outline = font.render(self.impact_text, True, (0, 0, 0))
            for ox, oy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
                outline_rect = outline.get_rect(
                    center=(text_rect.centerx + ox * scale, text_rect.centery + oy * scale)
                )
                surface.blit(outline, outline_rect)
            surface.blit(text_surf, text_rect)


class HealAllEffect(CardVisualEffect):
    def __init__(self, game, size=100, travel_duration=0.5, squish_hold=1.4, spawn_spread=0.5):
        self.game = game

        target_units = game.player_team + game.enemy_team

        super().__init__(spawn_spread + travel_duration + squish_hold)

        self.size = size
        self.travel_duration = travel_duration
        self.squish_hold = squish_hold
        self.spawn_spread = spawn_spread

        self.target_units = target_units
        self.delays = [random.uniform(0, spawn_spread) for _ in target_units]

        self.image = _load_image("assets/medic.png")

    def draw(self, surface):
        scale = _scale(self.game)
        size = max(1, int(self.size * scale))
        base_image = pygame.transform.smoothscale(self.image, (size, size))
        start_pos = (self.game.screen.width // 2, -50 * scale)

        for i, unit in enumerate(self.target_units):
            local_elapsed = self.elapsed - self.delays[i]
            if local_elapsed < 0:
                continue

            rect = self.game.get_unit_rect(unit)
            if not rect:
                continue
            target_x, target_y = rect.center

            if local_elapsed <= self.travel_duration:
                t = local_elapsed / self.travel_duration if self.travel_duration else 1.0
                x = HealAllEffect._lerp(start_pos[0], target_x, t)
                y = HealAllEffect._lerp(start_pos[1], target_y, t)
                img_rect = base_image.get_rect(center=(x, y))
                surface.blit(base_image, img_rect)
            elif local_elapsed <= self.travel_duration + self.squish_hold:
                squish_t = (local_elapsed - self.travel_duration) / self.squish_hold if self.squish_hold else 1.0
                punch = math.sin(squish_t * math.pi)
                stretch_x = 1 + 0.4 * punch
                stretch_y = 1 - 0.4 * punch
                w = max(1, int(size * stretch_x))
                h = max(1, int(size * stretch_y))
                squished_image = pygame.transform.smoothscale(self.image, (w, h))
                img_rect = squished_image.get_rect(center=(target_x, target_y))
                surface.blit(squished_image, img_rect)

    def _lerp(a, b, p):
        return a + p * (b-a)


class _RainDrop:

    def __init__(self, x_frac, delay):
        self.x_frac = x_frac
        self.delay = delay
        self.positions = []


class RainEffect(CardVisualEffect):
    def __init__(self, game, image_path, source_unit, target_unit,
                 duration=0.4, size=140, spin_speed=1440,
                 impact_hold=0.35, trail_length=6,
                 drop_count=14, spawn_spread=0.6, show_impact_text=False):
        super().__init__(spawn_spread + duration + impact_hold)
        self.game = game
        self.image = _load_image(image_path)
        self.fly_duration = duration
        self.impact_hold = impact_hold
        self.size = size
        self.spin_speed = spin_speed
        self.trail_length = trail_length
        self.spawn_spread = spawn_spread
        self.show_impact_text = show_impact_text
        

        self.drops = [
            _RainDrop(
                x_frac=random.random(),
                delay=random.uniform(0, spawn_spread),
            )
            for _ in range(drop_count)
        ]
        self._text_drawn = False

    def _unit_pos(self, unit, fallback):
        rect = self.game.get_unit_rect(unit)
        return rect.center if rect else fallback

    def _drop_endpoints(self, drop, scale):
        x = drop.x_frac * self.game.screen.width
        top = -50 * scale
        bottom = self.game.screen.height
        return (x, top), (x, bottom)

    def update(self, dt):
        super().update(dt)
        scale = _scale(self.game)
        for drop in self.drops:
            local_elapsed = self.elapsed - drop.delay
            if 0 <= local_elapsed <= self.fly_duration:
                drop.positions.append(self._current_pos(drop, local_elapsed, scale))
                if len(drop.positions) > self.trail_length:
                    drop.positions.pop(0)

    def _current_pos(self, drop, local_elapsed, scale):
        start_pos, end_pos = self._drop_endpoints(drop, scale)
        t = min(1.0, local_elapsed / self.fly_duration) if self.fly_duration > 0 else 1.0
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
        y += math.sin(t * math.pi * 6) * 10 * scale
        return x, y

    def draw(self, surface):
        self._text_drawn = False
        scale = _scale(self.game)
        for drop in self.drops:
            local_elapsed = self.elapsed - drop.delay
            if local_elapsed < 0:
                continue
            elif local_elapsed <= self.fly_duration:
                self._draw_flight(surface, drop, scale)
            elif local_elapsed <= self.fly_duration + self.impact_hold:
                self._draw_impact(surface, drop, local_elapsed, scale)

    def _draw_flight(self, surface, drop, scale):
        positions = drop.positions
        count = max(1, len(positions))
        angle = self.elapsed * self.spin_speed
        for i, pos in enumerate(positions):
            fade = int(255 * (i + 1) / count)
            size = int(self.size * scale * (0.5 + 0.5 * (i + 1) / count))
            img = pygame.transform.smoothscale(self.image, (max(1, size), max(1, size)))
            img = pygame.transform.rotate(img, angle)
            img.set_alpha(fade)
            rect = img.get_rect(center=pos)
            surface.blit(img, rect)

    def _draw_impact(self, surface, drop, local_elapsed, scale):
        t = (local_elapsed - self.fly_duration) / self.impact_hold if self.impact_hold else 1.0
        t = min(1.0, max(0.0, t))
        wobble = 1 + 0.4 * math.sin(t * math.pi * 10)
        size = int(self.size * scale * 1.6 * wobble)
        img = pygame.transform.smoothscale(self.image, (max(1, size), max(1, size)))
        _, end_pos = self._drop_endpoints(drop, scale)
        rect = img.get_rect(center=end_pos)
        surface.blit(img, rect)


class HeartRainEffect(CardVisualEffect):
    def __init__(self, game, unit, size=60, travel_duration=0.5, hold=0.6, spawn_spread=0.4):
        self.game = game

        team = game.player_team if unit in game.player_team else game.enemy_team
        target_units = [u for u in team if not u.is_dead]

        super().__init__(spawn_spread + travel_duration + hold)

        self.size = size
        self.travel_duration = travel_duration
        self.hold = hold
        self.spawn_spread = spawn_spread

        self.target_units = target_units
        self.delays = [random.uniform(0, spawn_spread) for _ in target_units]

        self.image = _load_image("assets/full_heart.png")

    def draw(self, surface):
        scale = _scale(self.game)
        size = max(1, int(self.size * scale))
        base_image = pygame.transform.smoothscale(self.image, (size, size))

        for i, unit in enumerate(self.target_units):
            local_elapsed = self.elapsed - self.delays[i]
            if local_elapsed < 0:
                continue

            rect = self.game.get_unit_rect(unit)
            if not rect:
                continue
            target_x, target_y = rect.center
            start_y = -50 * scale

            if local_elapsed <= self.travel_duration:
                t = local_elapsed / self.travel_duration if self.travel_duration else 1.0
                y = start_y + (target_y - start_y) * t
                rect_img = base_image.get_rect(center=(target_x, y))
                surface.blit(base_image, rect_img)
            elif local_elapsed <= self.travel_duration + self.hold:
                hold_t = (local_elapsed - self.travel_duration) / self.hold if self.hold else 1.0
                bounce = 1 + 0.25 * math.sin(hold_t * math.pi)
                w = max(1, int(size * bounce))
                h = max(1, int(size * bounce))
                bounced = pygame.transform.smoothscale(self.image, (w, h))
                rect_img = bounced.get_rect(center=(target_x, target_y))
                surface.blit(bounced, rect_img)


CARD_VISUAL_EFFECTS = {
    "explosion": lambda game, source, target: ProjectileEffect(
        game, "assets/fireball.png", source, target,
        duration=0.7, size=140, spin_speed=0, impact_text="KABLOEYY", impact_hold=.6
    ),

    "lazer": lambda game, source, target: ProjectileEffect(
        game, "assets/lazer.png", source, target,
        duration=.5, size=140, spin_speed=0, impact_text="ZZZZ", impact_hold=.4, trail_length=20
    ),
    
    "cuck": lambda game, source, target: RainEffect(
        game, "assets/lightning.png", source, target,
        duration=.5, size=140, spin_speed=0, impact_hold=.8, trail_length=5,  show_impact_text= False
    ),
    
    "ace": lambda game, source, target: RainEffect(
        game, "assets/card.png", source, target,
        duration=.5, size=140, spin_speed=10, impact_hold=0, trail_length=5, show_impact_text= False
    ),    
    "hospital": lambda game, source, target: HealAllEffect(
        game
    )
    
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


PASSIVE_VISUAL_EFFECTS = {
    ("penguin", Trigger.ON_DEATH): lambda game, unit, target: HeartRainEffect(game, unit),
}


def spawn_passive_effect(game, unit, trigger, target):
    factory = PASSIVE_VISUAL_EFFECTS.get((unit.name, trigger))
    if factory is None:
        return

    effect = factory(game, unit, target)
    if effect is None:
        return

    if isinstance(effect, list):
        game.visual_effects.extend(effect)
    else:
        game.visual_effects.append(effect)