import random

import pygame

from card import CARD_NAMES, create_card
from units import UNIT_SHOP_POOL, get_unit_price


SHOP_STOCK_SIZE = 4
UNIT_STOCK_SIZE = 2

BG_COLOR = (24, 22, 30)
PANEL_COLOR = (40, 38, 50)
TEXT_COLOR = (235, 235, 235)
PRICE_COLOR = (255, 215, 80)
DISABLED_COLOR = (120, 60, 60)
OVERLAY_COLOR = (0, 0, 0, 180)


BUTTON_ASPECT = 300 / 1000

_card_image_cache = {}
_unit_image_cache = {}
_button_image_cache = {}
_shopkeeper_image = None
_coin_image = None


def _load_card_image(name):
    if name not in _card_image_cache:
        _card_image_cache[name] = create_card(name).get_image()
    return _card_image_cache[name]


def _load_button_image(name):
    if name not in _button_image_cache:
        _button_image_cache[name] = pygame.image.load(f"assets/{name}.png").convert_alpha()
    return _button_image_cache[name]


def _load_unit_image(name):
    if name not in _unit_image_cache:
        _unit_image_cache[name] = pygame.image.load(f"unit/{name}.png").convert_alpha()
    return _unit_image_cache[name]


def _load_shopkeeper_image():
    global _shopkeeper_image
    if _shopkeeper_image is None:
        _shopkeeper_image = pygame.image.load("assets/shopkeeper.png").convert_alpha()
    return _shopkeeper_image


def _load_coin_image():
    global _coin_image
    if _coin_image is None:
        _coin_image = pygame.image.load("assets/coin.png").convert_alpha()
    return _coin_image


def get_card_price(card):
    return max(1, int(card.get_shop_price()))


class ShopScreen:
    def __init__(self, screen, player_state, on_close=None):
        self.screen = screen
        self.player_state = player_state
        self.on_close = on_close

        self.node = None
        self.card_stock = []
        self.unit_stock = []

        self.pending_unit_purchase = None
        self.pending_unit_price = 0

        self._font = None
        self._small_font = None
        self._title_font = None

        self._close_button_rect = None
        self._card_rects = []
        self._unit_rects = []
        self._team_slot_rects = []
        self._cancel_swap_rect = None

    def _fonts(self):
        if self._font is None:
            self._font = pygame.font.SysFont("comicsansms", max(14, int(self.screen.height * 0.028)))
            self._small_font = pygame.font.SysFont("comicsansms", max(12, int(self.screen.height * 0.022)))
            self._title_font = pygame.font.SysFont("comicsansms", max(18, int(self.screen.height * 0.04)), bold=True)
        return self._font, self._small_font, self._title_font

    def _draw_image_button(self, surface, image_name, anchor, pos, width_frac):
        width = int(self.screen.width * width_frac)
        height = int(width * BUTTON_ASPECT)
        image = pygame.transform.smoothscale(_load_button_image(image_name), (width, height))
        rect = image.get_rect(**{anchor: pos})
        surface.blit(image, rect)
        return rect

    def open(self, node):
        self.node = node
        self.pending_unit_purchase = None

        if node.shop_stock is None:
            pool = list(CARD_NAMES)
            random.shuffle(pool)
            node.shop_stock = pool[:SHOP_STOCK_SIZE]
        self.card_stock = node.shop_stock

        if node.unit_stock is None:
            pool = list(UNIT_SHOP_POOL)
            random.shuffle(pool)
            node.unit_stock = pool[:UNIT_STOCK_SIZE]
        self.unit_stock = node.unit_stock

    def handle_mousedown(self, pos):
        pass

    def handle_mouseup(self, pos):
        if self.pending_unit_purchase is not None:
            self._handle_swap_click(pos)
            return

        if self._close_button_rect is not None and self._close_button_rect.collidepoint(pos):
            if self.on_close is not None:
                self.on_close()
            return

        for rect, card_name in self._card_rects:
            if rect.collidepoint(pos):
                self._try_buy_card(card_name)
                return

        for rect, unit_name in self._unit_rects:
            if rect.collidepoint(pos):
                self._start_unit_purchase(unit_name)
                return

    def _try_buy_card(self, card_name):
        if card_name not in self.card_stock:
            return
        card = create_card(card_name)
        price = get_card_price(card)
        if self.player_state.spend_coins(price):
            self.player_state.add_to_pool(card_name, 1)
            self.card_stock.remove(card_name)

    def _start_unit_purchase(self, unit_name):
        if unit_name not in self.unit_stock:
            return
        price = get_unit_price(unit_name)
        if self.player_state.coins < price:
            return
        self.pending_unit_purchase = unit_name
        self.pending_unit_price = price

    def _handle_swap_click(self, pos):
        if self._cancel_swap_rect is not None and self._cancel_swap_rect.collidepoint(pos):
            self.pending_unit_purchase = None
            return

        for rect, index in self._team_slot_rects:
            if rect.collidepoint(pos):
                if self.player_state.spend_coins(self.pending_unit_price):
                    self.player_state.replace_team_unit(index, self.pending_unit_purchase)
                    self.unit_stock.remove(self.pending_unit_purchase)
                self.pending_unit_purchase = None
                return

    def draw(self):
        surface = self.screen.get_surface()
        surface.fill(BG_COLOR)

        self._draw_shopkeeper(surface)
        self._draw_header(surface)
        self._draw_coin_counter(surface)
        self._draw_card_section(surface)
        self._draw_unit_section(surface)
        self._draw_close_button(surface)

        if self.pending_unit_purchase is not None:
            self._draw_swap_overlay(surface)

    def _draw_shopkeeper(self, surface):
        image = _load_shopkeeper_image()
        height = int(self.screen.height * 0.5)
        width = height
        scaled = pygame.transform.smoothscale(image, (width, height))
        rect = scaled.get_rect(bottomleft=(int(self.screen.width * 0.02), self.screen.height))
        surface.blit(scaled, rect)

    def _draw_header(self, surface):
        font, small_font, title_font = self._fonts()

        title = title_font.render("Shop", True, TEXT_COLOR)
        surface.blit(title, title.get_rect(midtop=(self.screen.width // 2, 24)))

    def _draw_coin_counter(self, surface):
        font, small_font, title_font = self._fonts()

        coin_size = int(self.screen.height * 0.05)
        coin_image = pygame.transform.smoothscale(_load_coin_image(), (coin_size, coin_size))
        coin_rect = coin_image.get_rect(topleft=(24, 24))
        surface.blit(coin_image, coin_rect)

        coin_text = font.render(str(self.player_state.coins), True, PRICE_COLOR)
        surface.blit(coin_text, coin_text.get_rect(midleft=(coin_rect.right + 8, coin_rect.centery)))

    def _draw_close_button(self, surface):
        self._close_button_rect = self._draw_image_button(
            surface, "back", "topright", (self.screen.width - 24, 24), 0.12
        )

    def _draw_card_section(self, surface):
        font, small_font, title_font = self._fonts()

        label = font.render("Cards", True, TEXT_COLOR)
        top = int(self.screen.height * 0.32)
        surface.blit(label, label.get_rect(midtop=(int(self.screen.width * 0.62), top)))

        card_w = int(self.screen.width * 0.1)
        card_h = int(card_w * 1.3)
        margin = int(self.screen.width * 0.02)

        columns = max(1, len(self.card_stock))
        total_w = columns * card_w + (columns - 1) * margin
        start_x = int(self.screen.width * 0.62) - total_w // 2
        y = top + label.get_height() + 16

        self._card_rects = []

        if not self.card_stock:
            empty_text = font.render("Sold out!", True, TEXT_COLOR)
            surface.blit(empty_text, empty_text.get_rect(center=(int(self.screen.width * 0.62), y + card_h // 2)))
            return

        for i, card_name in enumerate(self.card_stock):
            x = start_x + i * (card_w + margin)
            rect = pygame.Rect(x, y, card_w, card_h)

            image = pygame.transform.smoothscale(_load_card_image(card_name), (card_w, card_h))
            surface.blit(image, rect)

            card = create_card(card_name)
            price = get_card_price(card)
            affordable = self.player_state.coins >= price

            if affordable:
                self._card_rects.append((rect, card_name))
            else:
                dim = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 130))
                surface.blit(dim, rect)

            price_color = PRICE_COLOR if affordable else DISABLED_COLOR
            price_text = small_font.render(str(price), True, price_color)
            surface.blit(price_text, price_text.get_rect(center=(rect.centerx, rect.bottom + 16)))

    def _draw_unit_section(self, surface):
        font, small_font, title_font = self._fonts()

        label = font.render("Units", True, TEXT_COLOR)
        top = int(self.screen.height * 0.62)
        surface.blit(label, label.get_rect(midtop=(int(self.screen.width * 0.62), top)))

        unit_size = int(self.screen.height * 0.16)
        margin = int(self.screen.width * 0.03)

        columns = max(1, len(self.unit_stock))
        total_w = columns * unit_size + (columns - 1) * margin
        start_x = int(self.screen.width * 0.62) - total_w // 2
        y = top + label.get_height() + 16

        self._unit_rects = []

        if not self.unit_stock:
            empty_text = font.render("Sold out!", True, TEXT_COLOR)
            surface.blit(empty_text, empty_text.get_rect(center=(int(self.screen.width * 0.62), y + unit_size // 2)))
            return

        for i, unit_name in enumerate(self.unit_stock):
            x = start_x + i * (unit_size + margin)
            rect = pygame.Rect(x, y, unit_size, unit_size)

            image = pygame.transform.smoothscale(_load_unit_image(unit_name), (unit_size, unit_size))
            surface.blit(image, rect)

            price = get_unit_price(unit_name)
            affordable = self.player_state.coins >= price

            if affordable:
                self._unit_rects.append((rect, unit_name))
            else:
                dim = pygame.Surface((unit_size, unit_size), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 130))
                surface.blit(dim, rect)

            name_color = TEXT_COLOR if affordable else DISABLED_COLOR
            name_text = small_font.render(unit_name.capitalize(), True, name_color)
            surface.blit(name_text, name_text.get_rect(midtop=(rect.centerx, rect.bottom + 6)))

            price_color = PRICE_COLOR if affordable else DISABLED_COLOR
            price_text = small_font.render(str(price), True, price_color)
            surface.blit(price_text, price_text.get_rect(midtop=(rect.centerx, rect.bottom + 6 + name_text.get_height() + 2)))

    def _draw_swap_overlay(self, surface):
        font, small_font, title_font = self._fonts()

        overlay = pygame.Surface((self.screen.width, self.screen.height), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        label = title_font.render(f"Swap in {self.pending_unit_purchase.capitalize()}", True, TEXT_COLOR)
        surface.blit(label, label.get_rect(midtop=(self.screen.width // 2, int(self.screen.height * 0.2))))

        team_names = self.player_state.team_names
        portrait_size = int(self.screen.height * 0.2)
        spacing = self.screen.width / (len(team_names) + 1)
        y = int(self.screen.height * 0.5)

        self._team_slot_rects = []

        for i, unit_name in enumerate(team_names):
            x = int(spacing * (i + 1))
            image = pygame.transform.smoothscale(_load_unit_image(unit_name), (portrait_size, portrait_size))
            rect = image.get_rect(center=(x, y))
            border_rect = rect.inflate(16, 16)

            pygame.draw.rect(surface, PANEL_COLOR, border_rect)
            surface.blit(image, rect)
            pygame.draw.rect(surface, TEXT_COLOR, border_rect, 3)

            name_text = small_font.render(unit_name.capitalize(), True, TEXT_COLOR)
            surface.blit(name_text, name_text.get_rect(midtop=(x, border_rect.bottom + 8)))

            self._team_slot_rects.append((border_rect, i))

        self._cancel_swap_rect = self._draw_image_button(
            surface, "back", "midtop", (self.screen.width // 2, int(self.screen.height * 0.78)), 0.12
        )