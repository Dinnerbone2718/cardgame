import random

import pygame

from player_state import EXTRA_HEART_AMOUNT


BG_COLOR = (24, 22, 30)
PANEL_COLOR = (40, 38, 50)
TEXT_COLOR = (235, 235, 235)
DISABLED_COLOR = (90, 90, 100)
HIGHLIGHT_COLOR = (255, 215, 80)

BUTTON_ASPECT = 300 / 1000

TICK_COUNT = 22
ROULETTE_DURATION = 2.6

UPGRADE_LABELS = {
    "extra_heart": "Extra Heart",
    "extra_card": "Extra Card",
    "glass_cannon": "Glass Cannon",
    "vision": "Vision",
}

_unit_image_cache = {}
_upgrade_image_cache = {}
_button_image_cache = {}


def _load_unit_image(name):
    if name not in _unit_image_cache:
        _unit_image_cache[name] = pygame.image.load(f"unit/{name}.png").convert_alpha()
    return _unit_image_cache[name]


def _load_upgrade_image(name):
    if name not in _upgrade_image_cache:
        _upgrade_image_cache[name] = pygame.image.load(f"upgrade/{name}.png").convert_alpha()
    return _upgrade_image_cache[name]


def _load_button_image(name):
    if name not in _button_image_cache:
        _button_image_cache[name] = pygame.image.load(f"assets/{name}.png").convert_alpha()
    return _button_image_cache[name]


class UpgradeScreen:
    def __init__(self, screen, player_state, on_close=None):
        self.screen = screen
        self.player_state = player_state
        self.on_close = on_close

        self.node = None
        self.state = "spinning"
        self.spin_elapsed = 0.0
        self.result = None

        self._sequence = []
        self._tick_durations = []
        self._cumulative = []

        self._font = None
        self._small_font = None
        self._title_font = None

        self._back_button_rect = None
        self._portrait_rects = {}

    def _fonts(self):
        if self._font is None:
            self._font = pygame.font.SysFont("comicsansms", max(14, int(self.screen.height * 0.028)))
            self._small_font = pygame.font.SysFont("comicsansms", max(12, int(self.screen.height * 0.022)))
            self._title_font = pygame.font.SysFont("comicsansms", max(18, int(self.screen.height * 0.04)), bold=True)
        return self._font, self._small_font, self._title_font

    def open(self, node):
        self.node = node
        self.state = "spinning"
        self.spin_elapsed = 0.0
        self._back_button_rect = None
        self._portrait_rects = {}

        pool = self._eligible_upgrade_pool()
        self.result = random.choice(pool)
        self._build_sequence(pool)

    def _eligible_upgrade_pool(self):
        pool = ["extra_heart", "extra_card", "vision"]
        if self.player_state.eligible_units_for_upgrade("glass_cannon"):
            pool.append("glass_cannon")
        return pool

    def _build_sequence(self, pool):
        self._sequence = [random.choice(pool) for _ in range(TICK_COUNT - 1)]
        self._sequence.append(self.result)

        raw_durations = []
        for i in range(TICK_COUNT):
            frac = i / (TICK_COUNT - 1)
            raw_durations.append(0.05 + frac * frac * 0.35)

        total = sum(raw_durations)
        scale = ROULETTE_DURATION / total
        self._tick_durations = [d * scale for d in raw_durations]

        self._cumulative = []
        running = 0.0
        for d in self._tick_durations:
            running += d
            self._cumulative.append(running)

    def _current_tick(self):
        for i, threshold in enumerate(self._cumulative):
            if self.spin_elapsed < threshold:
                start = self._cumulative[i - 1] if i > 0 else 0.0
                return i, self._tick_durations[i], start

        last = len(self._sequence) - 1
        start = self._cumulative[last - 1] if last > 0 else 0.0
        return last, self._tick_durations[last], start

    def update(self, dt):
        if self.state != "spinning":
            return
        self.spin_elapsed += dt
        if self.spin_elapsed >= ROULETTE_DURATION:
            self.state = "result"

    def handle_mousedown(self, pos):
        pass

    def handle_mouseup(self, pos):
        if self.state != "result":
            return

        if self._back_button_rect is not None and self._back_button_rect.collidepoint(pos):
            if self.on_close is not None:
                self.on_close()
            return

        for unit_name, rect in self._portrait_rects.items():
            if rect.collidepoint(pos):
                self.player_state.apply_upgrade(unit_name, self.result)
                if self.on_close is not None:
                    self.on_close()
                return

    def draw(self):
        surface = self.screen.get_surface()
        surface.fill(BG_COLOR)

        if self.state == "spinning":
            self._draw_spinning(surface)
        else:
            self._draw_result(surface)

    def _draw_spinning(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render("Rolling Upgrade...", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

        index, tick_duration, tick_start = self._current_tick()
        name = self._sequence[index]

        local_elapsed = self.spin_elapsed - tick_start
        local_t = min(1.0, local_elapsed / tick_duration) if tick_duration else 1.0
        pulse = 1.0 - 0.15 * local_t

        size = max(1, int(self.screen.height * 0.32 * pulse))
        image = pygame.transform.smoothscale(_load_upgrade_image(name), (size, size))
        rect = image.get_rect(center=(self.screen.width // 2, int(self.screen.height * 0.48)))
        surface.blit(image, rect)

        label = font.render(UPGRADE_LABELS.get(name, name), True, TEXT_COLOR)
        surface.blit(label, label.get_rect(midtop=(self.screen.width // 2, rect.bottom + 20)))

    def _draw_result(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render(UPGRADE_LABELS.get(self.result, self.result), True, HIGHLIGHT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

        icon_size = int(self.screen.height * 0.2)
        icon = pygame.transform.smoothscale(_load_upgrade_image(self.result), (icon_size, icon_size))
        icon_rect = icon.get_rect(midtop=(self.screen.width // 2, int(self.screen.height * 0.1)))
        surface.blit(icon, icon_rect)

        subtitle = small_font.render("Choose a unit", True, TEXT_COLOR)
        subtitle_rect = subtitle.get_rect(midtop=(self.screen.width // 2, icon_rect.bottom + 12))
        surface.blit(subtitle, subtitle_rect)

        self._draw_unit_grid(surface, font, small_font, subtitle_rect.bottom + 24)
        self._draw_back_button(surface)

    def _draw_unit_grid(self, surface, font, small_font, top):
        team_names = self.player_state.team_names
        eligible = set(self.player_state.eligible_units_for_upgrade(self.result))

        count = len(team_names)
        portrait_size = int(self.screen.height * 0.24)
        spacing = self.screen.width / (count + 1)

        self._portrait_rects = {}

        for i, unit_name in enumerate(team_names):
            x = int(spacing * (i + 1))
            y = int(top + portrait_size // 2)

            image = pygame.transform.smoothscale(_load_unit_image(unit_name), (portrait_size, portrait_size))
            rect = image.get_rect(center=(x, y))
            border_rect = rect.inflate(20, 20)

            pygame.draw.rect(surface, PANEL_COLOR, border_rect)
            surface.blit(image, rect)

            is_eligible = unit_name in eligible

            if not is_eligible:
                dim = pygame.Surface(border_rect.size, pygame.SRCALPHA)
                dim.fill((0, 0, 0, 160))
                surface.blit(dim, border_rect)
            else:
                self._portrait_rects[unit_name] = border_rect

            border_color = TEXT_COLOR if is_eligible else DISABLED_COLOR
            pygame.draw.rect(surface, border_color, border_rect, 3)

            name_text = font.render(unit_name.capitalize(), True, TEXT_COLOR)
            surface.blit(name_text, name_text.get_rect(midtop=(x, border_rect.bottom + 12)))

            info_bits = self._unit_info_bits(unit_name)
            if info_bits:
                info_text = small_font.render(", ".join(info_bits), True, HIGHLIGHT_COLOR)
                surface.blit(info_text, info_text.get_rect(midtop=(x, border_rect.bottom + 12 + name_text.get_height() + 4)))

    def _unit_info_bits(self, unit_name):
        upgrades = self.player_state.get_upgrades(unit_name)
        info_bits = []
        if upgrades["extra_heart"]:
            info_bits.append(f"+{upgrades['extra_heart'] * EXTRA_HEART_AMOUNT} HP")
        if upgrades["extra_card"]:
            info_bits.append(f"+{upgrades['extra_card']} draw")
        if upgrades["glass_cannon"]:
            info_bits.append("Glass Cannon")
        if upgrades["vision"]:
            info_bits.append("Vision")
        return info_bits

    def _draw_back_button(self, surface):
        width = int(self.screen.width * 0.14)
        height = int(width * BUTTON_ASPECT)
        image = pygame.transform.smoothscale(_load_button_image("back"), (width, height))
        rect = image.get_rect(topright=(self.screen.width - 24, 24))
        surface.blit(image, rect)
        self._back_button_rect = rect