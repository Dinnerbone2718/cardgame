import pygame

from card import CARD_NAMES, create_card
from player_state import DECK_SIZE


_unit_image_cache = {}
_card_image_cache = {}
_button_image_cache = {}


def _load_unit_image(name):
    if name not in _unit_image_cache:
        _unit_image_cache[name] = pygame.image.load(f"unit/{name}.png").convert_alpha()
    return _unit_image_cache[name]


def _load_card_image(name):
    if name not in _card_image_cache:
        _card_image_cache[name] = create_card(name).get_image()
    return _card_image_cache[name]


def _load_button_image(name):
    if name not in _button_image_cache:
        _button_image_cache[name] = pygame.image.load(f"assets/{name}.png").convert_alpha()
    return _button_image_cache[name]


BUTTON_ASPECT = 300 / 1000


BG_COLOR = (24, 22, 30)
PANEL_COLOR = (40, 38, 50)
COMPLETE_COLOR = (110, 200, 120)
INCOMPLETE_COLOR = (200, 90, 90)
TEXT_COLOR = (235, 235, 235)
DISABLED_COLOR = (90, 90, 100)


class DeckScreen:
    def __init__(self, screen, player_state, on_close=None):
        self.screen = screen
        self.player_state = player_state
        self.on_close = on_close

        self.selected_unit = None
        self.draft_deck = []

        self._font = None
        self._small_font = None
        self._title_font = None

        self._portrait_rects = {}
        self._close_button_rect = None
        self._back_button_rect = None
        self._save_button_rect = None
        self._draft_card_rects = []
        self._pool_card_rects = []

    def _fonts(self):
        if self._font is None:
            self._font = pygame.font.SysFont("comicsansms", max(14, int(self.screen.height * 0.028)))
            self._small_font = pygame.font.SysFont("comicsansms", max(12, int(self.screen.height * 0.022)))
            self._title_font = pygame.font.SysFont("comicsansms", max(18, int(self.screen.height * 0.04)), bold=True)
        return self._font, self._small_font, self._title_font

    def _draw_image_button(self, surface, image_name, anchor, pos, width_frac, disabled=False):
        width = int(self.screen.width * width_frac)
        height = int(width * BUTTON_ASPECT)
        image = pygame.transform.smoothscale(_load_button_image(image_name), (width, height))
        if disabled:
            image = image.copy()
            dim = pygame.Surface((width, height), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            image.blit(dim, (0, 0))
        rect = image.get_rect(**{anchor: pos})
        surface.blit(image, rect)
        return rect

    def open(self):
        self.selected_unit = None
        self.draft_deck = []

    def handle_mousedown(self, pos):
        pass

    def handle_mouseup(self, pos):
        if self.selected_unit is None:
            self._handle_grid_click(pos)
        else:
            self._handle_edit_click(pos)

    def _handle_grid_click(self, pos):
        if self._close_button_rect is not None and self._close_button_rect.collidepoint(pos):
            if self.on_close is not None:
                self.on_close()
            return

        for unit_name, rect in self._portrait_rects.items():
            if rect.collidepoint(pos):
                self.selected_unit = unit_name
                self.draft_deck = list(self.player_state.unit_decks.get(unit_name, []))
                return

    def _handle_edit_click(self, pos):
        if self._back_button_rect is not None and self._back_button_rect.collidepoint(pos):
            self.selected_unit = None
            self.draft_deck = []
            return

        if self._save_button_rect is not None and self._save_button_rect.collidepoint(pos):
            if len(self.draft_deck) == DECK_SIZE:
                self.player_state.unit_decks[self.selected_unit] = list(self.draft_deck)
                self.selected_unit = None
                self.draft_deck = []
            return

        for rect, index in self._draft_card_rects:
            if rect.collidepoint(pos):
                self.draft_deck.pop(index)
                return

        for rect, card_name in self._pool_card_rects:
            if rect.collidepoint(pos):
                self._try_add_card(card_name)
                return

    def _try_add_card(self, card_name):
        if len(self.draft_deck) >= DECK_SIZE:
            return
        remaining = self.player_state.available_count(card_name, exclude_unit=self.selected_unit)
        remaining -= self.draft_deck.count(card_name)
        if remaining > 0:
            self.draft_deck.append(card_name)

    def draw(self):
        surface = self.screen.get_surface()
        surface.fill(BG_COLOR)

        if self.selected_unit is None:
            self._draw_grid(surface)
        else:
            self._draw_edit(surface)

    def _draw_grid(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render("Manage Decks", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

        self._close_button_rect = self._draw_image_button(
            surface, "back", "topright", (self.screen.width - 24, 24), 0.14
        )

        team_names = self.player_state.team_names
        count = len(team_names)
        portrait_size = int(self.screen.height * 0.28)
        spacing = self.screen.width / (count + 1)

        self._portrait_rects = {}

        for i, unit_name in enumerate(team_names):
            x = int(spacing * (i + 1))
            y = self.screen.height // 2 - portrait_size // 2

            image = pygame.transform.smoothscale(_load_unit_image(unit_name), (portrait_size, portrait_size))
            rect = image.get_rect(topleft=(x - portrait_size // 2, y))
            border_rect = rect.inflate(20, 20)

            pygame.draw.rect(surface, PANEL_COLOR, border_rect)
            surface.blit(image, rect)

            deck = self.player_state.unit_decks.get(unit_name, [])
            valid = len(deck) == DECK_SIZE
            color = COMPLETE_COLOR if valid else INCOMPLETE_COLOR
            pygame.draw.rect(surface, color, border_rect, 4)

            name_text = font.render(unit_name.capitalize(), True, TEXT_COLOR)
            surface.blit(name_text, name_text.get_rect(midtop=(x, border_rect.bottom + 16)))

            count_text = small_font.render(f"{len(deck)}/{DECK_SIZE} cards", True, color)
            surface.blit(count_text, count_text.get_rect(midtop=(x, border_rect.bottom + 16 + name_text.get_height() + 4)))

            self._portrait_rects[unit_name] = border_rect

    def _draw_edit(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render(f"{self.selected_unit.capitalize()}'s Deck", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

        self._back_button_rect = self._draw_image_button(
            surface, "back", "topleft", (24, 24), 0.12
        )

        valid = len(self.draft_deck) == DECK_SIZE
        self._save_button_rect = self._draw_image_button(
            surface, "save_deck", "topright", (self.screen.width - 24, 24), 0.16, disabled=not valid
        )

        count_text = small_font.render(f"{len(self.draft_deck)}/{DECK_SIZE}", True, TEXT_COLOR if valid else INCOMPLETE_COLOR)
        surface.blit(count_text, count_text.get_rect(midtop=(self._save_button_rect.centerx, self._save_button_rect.bottom + 4)))

        self._draw_draft_section(surface, font, small_font)
        self._draw_pool_section(surface, font, small_font)

    def _draw_draft_section(self, surface, font, small_font):
        label = font.render("Current Deck (click to remove)", True, TEXT_COLOR)
        top = int(self.screen.height * 0.14)
        surface.blit(label, label.get_rect(midtop=(self.screen.width // 2, top)))

        card_w = int(self.screen.width * 0.07)
        card_h = int(card_w * 1.3)
        columns = DECK_SIZE
        margin = int(self.screen.width * 0.01)
        total_w = columns * card_w + (columns - 1) * margin
        start_x = self.screen.width // 2 - total_w // 2
        y = top + label.get_height() + 16

        self._draft_card_rects = []

        for i in range(columns):
            x = start_x + i * (card_w + margin)
            rect = pygame.Rect(x, y, card_w, card_h)
            if i < len(self.draft_deck):
                card_name = self.draft_deck[i]
                image = pygame.transform.smoothscale(_load_card_image(card_name), (card_w, card_h))
                surface.blit(image, rect)
                self._draft_card_rects.append((rect, i))
            else:
                pygame.draw.rect(surface, PANEL_COLOR, rect)
            pygame.draw.rect(surface, TEXT_COLOR, rect, 2)

    def _draw_pool_section(self, surface, font, small_font):
        label = font.render("Card Pool (click to add)", True, TEXT_COLOR)
        top = int(self.screen.height * 0.42)
        surface.blit(label, label.get_rect(midtop=(self.screen.width // 2, top)))

        card_w = int(self.screen.width * 0.08)
        card_h = int(card_w * 1.3)
        columns = len(CARD_NAMES)
        margin = int(self.screen.width * 0.015)
        total_w = columns * card_w + (columns - 1) * margin
        start_x = self.screen.width // 2 - total_w // 2
        y = top + label.get_height() + 24

        self._pool_card_rects = []

        for i, card_name in enumerate(CARD_NAMES):
            x = start_x + i * (card_w + margin)
            rect = pygame.Rect(x, y, card_w, card_h)

            remaining = self.player_state.available_count(card_name, exclude_unit=self.selected_unit)
            remaining -= self.draft_deck.count(card_name)

            image = pygame.transform.smoothscale(_load_card_image(card_name), (card_w, card_h))
            surface.blit(image, rect)

            if remaining <= 0:
                dim = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 160))
                surface.blit(dim, rect)
            else:
                self._pool_card_rects.append((rect, card_name))

            pygame.draw.rect(surface, TEXT_COLOR, rect, 2)

            count_text = small_font.render(str(max(0, remaining)), True, TEXT_COLOR)
            surface.blit(count_text, count_text.get_rect(center=(rect.centerx, rect.bottom + 14)))