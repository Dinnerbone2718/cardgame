import random

import pygame

from card import HIGH_TIER_CARDS, create_card


BG_COLOR = (24, 22, 30)
TEXT_COLOR = (235, 235, 235)
HIGHLIGHT_COLOR = (255, 215, 80)

BUTTON_ASPECT = 300 / 1000

CHOICE_COUNT = 3

_card_image_cache = {}
_button_image_cache = {}


def _load_card_image(name):
    if name not in _card_image_cache:
        _card_image_cache[name] = create_card(name).get_image()
    return _card_image_cache[name]


def _load_button_image(name):
    if name not in _button_image_cache:
        _button_image_cache[name] = pygame.image.load(f"assets/{name}.png").convert_alpha()
    return _button_image_cache[name]


class CardScreen:
    def __init__(self, screen, player_state, on_close=None):
        self.screen = screen
        self.player_state = player_state
        self.on_close = on_close

        self.node = None
        self.choices = []
        self.chosen_card = None

        self._font = None
        self._small_font = None
        self._title_font = None

        self._card_rects = []
        self._back_button_rect = None

    def _fonts(self):
        if self._font is None:
            self._font = pygame.font.SysFont("comicsansms", max(14, int(self.screen.height * 0.028)))
            self._small_font = pygame.font.SysFont("comicsansms", max(12, int(self.screen.height * 0.022)))
            self._title_font = pygame.font.SysFont("comicsansms", max(18, int(self.screen.height * 0.04)), bold=True)
        return self._font, self._small_font, self._title_font

    def open(self, node):
        self.node = node
        self.chosen_card = None
        self._back_button_rect = None

        pool = list(HIGH_TIER_CARDS)
        random.shuffle(pool)
        if len(pool) >= CHOICE_COUNT:
            self.choices = pool[:CHOICE_COUNT]
        else:
            self.choices = [random.choice(HIGH_TIER_CARDS) for _ in range(CHOICE_COUNT)]

    def handle_mousedown(self, pos):
        pass

    def handle_mouseup(self, pos):
        if self.chosen_card is not None:
            if self._back_button_rect is not None and self._back_button_rect.collidepoint(pos):
                if self.on_close is not None:
                    self.on_close()
            return

        for rect, card_name in self._card_rects:
            if rect.collidepoint(pos):
                self.player_state.add_to_pool(card_name, 1)
                self.chosen_card = card_name
                return

    def draw(self):
        surface = self.screen.get_surface()
        surface.fill(BG_COLOR)

        if self.chosen_card is None:
            self._draw_choices(surface)
        else:
            self._draw_result(surface)

    def _draw_choices(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render("Choose a Card", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

        subtitle = small_font.render("A rare, powerful card for your collection", True, HIGHLIGHT_COLOR)
        surface.blit(subtitle, subtitle.get_rect(midtop=(self.screen.width // 2, 24 + title.get_height() + 6)))

        card_w = int(self.screen.width * 0.14)
        card_h = int(card_w * 1.3)
        margin = int(self.screen.width * 0.04)

        columns = max(1, len(self.choices))
        total_w = columns * card_w + (columns - 1) * margin
        start_x = self.screen.width // 2 - total_w // 2
        y = self.screen.height // 2 - card_h // 2

        self._card_rects = []

        for i, card_name in enumerate(self.choices):
            x = start_x + i * (card_w + margin)
            rect = pygame.Rect(x, y, card_w, card_h)

            image = pygame.transform.smoothscale(_load_card_image(card_name), (card_w, card_h))
            surface.blit(image, rect)
            pygame.draw.rect(surface, HIGHLIGHT_COLOR, rect, 3)

            name_text = font.render(card_name.capitalize(), True, TEXT_COLOR)
            surface.blit(name_text, name_text.get_rect(midtop=(rect.centerx, rect.bottom + 12)))

            self._card_rects.append((rect, card_name))

    def _draw_result(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render(f"Added {self.chosen_card.capitalize()}!", True, HIGHLIGHT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

        card_w = int(self.screen.width * 0.18)
        card_h = int(card_w * 1.3)
        image = pygame.transform.smoothscale(_load_card_image(self.chosen_card), (card_w, card_h))
        rect = image.get_rect(center=(self.screen.width // 2, int(self.screen.height * 0.45)))
        surface.blit(image, rect)

        self._draw_back_button(surface)

    def _draw_back_button(self, surface):
        width = int(self.screen.width * 0.14)
        height = int(width * BUTTON_ASPECT)
        image = pygame.transform.smoothscale(_load_button_image("back"), (width, height))
        rect = image.get_rect(midtop=(self.screen.width // 2, int(self.screen.height * 0.72)))
        surface.blit(image, rect)
        self._back_button_rect = rect