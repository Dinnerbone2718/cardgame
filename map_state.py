import math
import pygame
import random

from map_node import MapNode
from units import ENEMY_UNIT_POOL, UNIT_POWER


NODE_IMAGE_FILES = {
    "combat": "world/combat.png",
    "shop": "world/shop.png",
    "upgrade": "world/upgrade.png",
    "boss": "world/boss.png",
    "card": "world/card.png",
    "start": "world/start.png"
}

NODE_RING_COLOR = (255, 215, 0)
VISITED_RING_COLOR = (110, 200, 120)
LINE_COLOR = (130, 130, 140)
LINE_COLOR_TRAVELLED = (110, 200, 120)
BG_COLOR = (24, 22, 30)

FIGHT_NODE_TYPES = ("combat", "boss")

FIGHT_CONFIG_OVERRIDES = {}

ENEMY_TEAM_SIZE = 4
DIFFICULTY_LEVELS = 5

MIN_POWER_BUDGET = ENEMY_TEAM_SIZE * min(UNIT_POWER.values())
MAX_POWER_BUDGET = ENEMY_TEAM_SIZE * (sum(UNIT_POWER.values()) / len(UNIT_POWER))
BOSS_POWER_BONUS = ENEMY_TEAM_SIZE * 2

CANDIDATE_POOL_SIZE = 3


def _progress_for_node(node):
    return min(1.0, max(0.0, node.x))


def _difficulty_for_progress(progress, is_boss):
    difficulty = 1 + round(progress * (DIFFICULTY_LEVELS - 1))
    if is_boss:
        difficulty += 1
    return max(1, min(DIFFICULTY_LEVELS, difficulty))


def _generate_enemy_team(progress, is_boss=False):
    budget = MIN_POWER_BUDGET + (MAX_POWER_BUDGET - MIN_POWER_BUDGET) * progress
    if is_boss:
        budget += BOSS_POWER_BONUS

    team = []
    remaining = budget

    for i in range(ENEMY_TEAM_SIZE):
        slots_left = ENEMY_TEAM_SIZE - i
        target = remaining / slots_left
        ranked = sorted(ENEMY_UNIT_POOL, key=lambda name: abs(UNIT_POWER[name] - target))
        chosen = random.choice(ranked[:CANDIDATE_POOL_SIZE])
        team.append(chosen)
        remaining -= UNIT_POWER[chosen]

    return team


def get_fight_config(node):
    override = FIGHT_CONFIG_OVERRIDES.get(node.id)
    if override is not None:
        return override

    if node.fight_config is None:
        progress = _progress_for_node(node)
        is_boss = node.node_type == "boss"
        node.fight_config = {
            "difficulty": _difficulty_for_progress(progress, is_boss),
            "enemy_team": _generate_enemy_team(progress, is_boss=is_boss),
        }

    return node.fight_config


def get_fight_difficulty(node):
    return get_fight_config(node).get("difficulty", 1)


MAP_ZOOM = 1.6

DRAG_THRESHOLD = 6

HINT_TEXT = "Drag to move the map"
HINT_DURATION = 4.0
HINT_FADE = 1.0


class MapState:
    def __init__(self, screen, nodes, start_node, player_state, zoom=MAP_ZOOM, on_combat_start=None, on_deck_button_click=None, on_shop_enter=None, on_upgrade_enter=None, on_card_enter=None):
        self.screen = screen
        self.nodes = nodes
        self.current_node = start_node
        self.current_node.visited = True

        self.player_state = player_state

        self.on_combat_start = on_combat_start
        self.on_deck_button_click = on_deck_button_click
        self.on_shop_enter = on_shop_enter
        self.on_upgrade_enter = on_upgrade_enter
        self.on_card_enter = on_card_enter

        self._images = {
            node_type: pygame.image.load(path).convert_alpha()
            for node_type, path in NODE_IMAGE_FILES.items()
        }

        self._hand_image_base = pygame.image.load("assets/finger.png").convert_alpha()
        self._hand_image = pygame.transform.rotate(self._hand_image_base, -90)

        self._box_image = pygame.image.load("assets/box.png").convert_alpha()
        self._full_heart_image = pygame.image.load("assets/full_heart.png").convert_alpha()
        self._fight_button_image = pygame.image.load("assets/fight.png").convert_alpha()
        self._deck_button_image = pygame.image.load("assets/deck.png").convert_alpha()
        self._coin_image = pygame.image.load("assets/coin.png").convert_alpha()
        self._enter_button_image = pygame.image.load("assets/enter.png").convert_alpha()

        self._fight_box_rect = None
        self._fight_button_rect = None
        self._deck_button_rect = None

        self._shop_box_rect = None
        self._shop_button_rect = None

        self._upgrade_box_rect = None
        self._upgrade_button_rect = None

        self._card_box_rect = None
        self._card_button_rect = None

        self._node_rects = {}
        self._bob_timer = 0.0
        self._hint_timer = 0.0
        self._font = None
        self._label_font = None
        self._enemy_icon_cache = {}

        self.pending_fight_node = None
        self.pending_shop_node = None
        self.pending_upgrade_node = None
        self.pending_card_node = None

        self.zoom = zoom

        self.camera_x = 0.0 
        self.camera_y = 0.0
        self._center_camera_on(self.current_node)

        self._mouse_down_pos = None
        self._mouse_down_cam = (0.0, 0.0)
        self._dragging = False
        self._mouse_pos = (-1, -1)

    def update(self, dt):
        self._bob_timer += dt
        self._hint_timer += dt
        self._clamp_camera()

    def _world_size(self):
        return self.screen.width * self.zoom, self.screen.height * self.zoom

    def _viewport_frac(self):
        return 1.0 / self.zoom, 1.0 / self.zoom

    def _center_camera_on(self, node):
        vp_w, vp_h = self._viewport_frac()
        self.camera_x = node.x - vp_w / 2
        self.camera_y = node.y - vp_h / 2
        self._clamp_camera()

    def _clamp_camera(self):
        vp_w, vp_h = self._viewport_frac()
        max_x = max(0.0, 1.0 - vp_w)
        max_y = max(0.0, 1.0 - vp_h)
        self.camera_x = min(max(self.camera_x, 0.0), max_x)
        self.camera_y = min(max(self.camera_y, 0.0), max_y)

    def handle_mousedown(self, pos):
        self._mouse_down_pos = pos
        self._mouse_down_cam = (self.camera_x, self.camera_y)
        self._dragging = False

    def handle_mousemotion(self, pos):
        self._mouse_pos = pos

        if self._mouse_down_pos is None:
            return

        dx = pos[0] - self._mouse_down_pos[0]
        dy = pos[1] - self._mouse_down_pos[1]

        if not self._dragging and (abs(dx) > DRAG_THRESHOLD or abs(dy) > DRAG_THRESHOLD):
            self._dragging = True

        if self._dragging:
            world_w, world_h = self._world_size()
            self.camera_x = self._mouse_down_cam[0] - dx / world_w
            self.camera_y = self._mouse_down_cam[1] - dy / world_h
            self._clamp_camera()

    def handle_mouseup(self, pos):
        if self._mouse_down_pos is not None and not self._dragging:
            if self._deck_button_rect is not None and self._deck_button_rect.collidepoint(pos):
                self._mouse_down_pos = None
                self._dragging = False
                if self.on_deck_button_click is not None:
                    self.on_deck_button_click()
                return

            clicked_node = self._handle_node_click(pos)
            if not clicked_node:
                if self.pending_fight_node is not None:
                    self._handle_fight_prompt_click(pos)
                elif self.pending_shop_node is not None:
                    self._handle_shop_prompt_click(pos)
                elif self.pending_upgrade_node is not None:
                    self._handle_upgrade_prompt_click(pos)
                elif self.pending_card_node is not None:
                    self._handle_card_prompt_click(pos)

        self._mouse_down_pos = None
        self._dragging = False

    def _handle_node_click(self, pos):
        for node, rect in self._node_rects.items():
            if not rect.collidepoint(pos):
                continue
            if node is self.current_node:
                return True
            if not self._is_reachable(node):
                return True

            if self._is_fight_node(node):
                self.pending_shop_node = None
                self.pending_upgrade_node = None
                self.pending_card_node = None
                self.pending_fight_node = node
            elif self._is_shop_node(node):
                self.pending_fight_node = None
                self.pending_upgrade_node = None
                self.pending_card_node = None
                self.pending_shop_node = node
            elif self._is_upgrade_node(node):
                self.pending_fight_node = None
                self.pending_shop_node = None
                self.pending_card_node = None
                self.pending_upgrade_node = node
            elif self._is_card_node(node):
                self.pending_fight_node = None
                self.pending_shop_node = None
                self.pending_upgrade_node = None
                self.pending_card_node = node
            else:
                self.pending_fight_node = None
                self.pending_shop_node = None
                self.pending_upgrade_node = None
                self.pending_card_node = None
                self._travel_to(node)
            return True
        return False

    def _handle_fight_prompt_click(self, pos):
        if self._fight_button_rect is not None and self._fight_button_rect.collidepoint(pos):
            self._enter_combat(self.pending_fight_node)
            return

        if self._fight_box_rect is not None and self._fight_box_rect.collidepoint(pos):
            return

        self.pending_fight_node = None
        self._fight_button_rect = None
        self._fight_box_rect = None

    def _handle_shop_prompt_click(self, pos):
        if self._shop_button_rect is not None and self._shop_button_rect.collidepoint(pos):
            self._enter_shop(self.pending_shop_node)
            return

        if self._shop_box_rect is not None and self._shop_box_rect.collidepoint(pos):
            return

        self.pending_shop_node = None
        self._shop_button_rect = None
        self._shop_box_rect = None

    def _handle_upgrade_prompt_click(self, pos):
        if self._upgrade_button_rect is not None and self._upgrade_button_rect.collidepoint(pos):
            self._enter_upgrade(self.pending_upgrade_node)
            return

        if self._upgrade_box_rect is not None and self._upgrade_box_rect.collidepoint(pos):
            return

        self.pending_upgrade_node = None
        self._upgrade_button_rect = None
        self._upgrade_box_rect = None

    def _handle_card_prompt_click(self, pos):
        if self._card_button_rect is not None and self._card_button_rect.collidepoint(pos):
            self._enter_card(self.pending_card_node)
            return

        if self._card_box_rect is not None and self._card_box_rect.collidepoint(pos):
            return

        self.pending_card_node = None
        self._card_button_rect = None
        self._card_box_rect = None

    def _is_reachable(self, node):
        return node in self.current_node.connections

    def _is_fight_node(self, node):
        return node.node_type in FIGHT_NODE_TYPES

    def _is_shop_node(self, node):
        return node.node_type == "shop" and not node.shop_entered

    def _is_upgrade_node(self, node):
        return node.node_type == "upgrade" and not node.upgrade_entered

    def _is_card_node(self, node):
        return node.node_type == "card" and not node.card_entered

    def _enter_combat(self, node):
        self.pending_fight_node = None
        self._fight_button_rect = None
        self._fight_box_rect = None
        self._travel_to(node)
        if self.on_combat_start is not None:
            self.on_combat_start(node)

    def _enter_shop(self, node):
        self.pending_shop_node = None
        self._shop_button_rect = None
        self._shop_box_rect = None
        node.shop_entered = True
        self._travel_to(node)
        if self.on_shop_enter is not None:
            self.on_shop_enter(node)

    def _enter_upgrade(self, node):
        self.pending_upgrade_node = None
        self._upgrade_button_rect = None
        self._upgrade_box_rect = None
        node.upgrade_entered = True
        self._travel_to(node)
        if self.on_upgrade_enter is not None:
            self.on_upgrade_enter(node)

    def _enter_card(self, node):
        self.pending_card_node = None
        self._card_button_rect = None
        self._card_box_rect = None
        node.card_entered = True
        self._travel_to(node)
        if self.on_card_enter is not None:
            self.on_card_enter(node)

    def _travel_to(self, node):
        self.current_node = node
        node.visited = True
        self._center_camera_on(node)

    def _node_size(self):
        return int(self.screen.height * 0.11)

    def draw(self):
        surface = self.screen.get_surface()
        surface.fill(BG_COLOR)

        self._draw_connections(surface)
        self._draw_nodes(surface)
        self._draw_hand(surface)
        self._draw_hint(surface)
        self._draw_fight_prompt(surface)
        self._draw_shop_prompt(surface)
        self._draw_upgrade_prompt(surface)
        self._draw_card_prompt(surface)
        self._draw_deck_button(surface)
        self._draw_coin_counter(surface)

    def _draw_deck_button(self, surface):
        width = int(self.screen.width * 0.16)
        height = int(width * (400 / 1000))
        scaled = pygame.transform.smoothscale(self._deck_button_image, (width, height))
        rect = scaled.get_rect(topleft=(16, 16))
        surface.blit(scaled, rect)
        self._deck_button_rect = rect

    def _draw_coin_counter(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont("comicsansms", max(16, int(self.screen.height * 0.07)))

        coin_size = int(self.screen.height * 0.05)
        coin_image = pygame.transform.smoothscale(self._coin_image, (coin_size, coin_size))
        coin_rect = coin_image.get_rect(topright=(self.screen.width - 24, 24))
        surface.blit(coin_image, coin_rect)

        text_surf = self._font.render(str(self.player_state.coins), True, (255, 215, 80))
        surface.blit(text_surf, text_surf.get_rect(midright=(coin_rect.left - 8, coin_rect.centery)))

    def _to_screen(self, x, y):
        world_w, world_h = self._world_size()
        return (x - self.camera_x) * world_w, (y - self.camera_y) * world_h

    def _draw_connections(self, surface):
        for node in self.nodes:
            for other in node.connections:
                travelled = node.visited and other.visited
                color = LINE_COLOR_TRAVELLED if travelled else LINE_COLOR
                pygame.draw.line(surface, color, self._to_screen(node.x, node.y), self._to_screen(other.x, other.y), 3)

    def _draw_nodes(self, surface):
        size = self._node_size()
        self._node_rects = {}

        for node in self.nodes:
            image = self._images.get(node.node_type)
            if image is None:
                continue

            screen_x, screen_y = self._to_screen(node.x, node.y)

            scaled = pygame.transform.smoothscale(image, (size, size))
            rect = scaled.get_rect(center=(int(screen_x), int(screen_y)))
            surface.blit(scaled, rect)

            if node is self.current_node:
                pygame.draw.circle(surface, NODE_RING_COLOR, rect.center, size // 2 + 6, 4)
            elif node.visited:
                pygame.draw.circle(surface, VISITED_RING_COLOR, rect.center, size // 2 + 4, 3)

            self._node_rects[node] = rect

    def _draw_hand(self, surface):
        rect = self._node_rects.get(self.current_node)
        if rect is None:
            return

        size = int(self._node_size() * 0.6)
        bob = math.sin(self._bob_timer * 4) * 6

        hand = pygame.transform.smoothscale(self._hand_image, (size, size))
        hand_rect = hand.get_rect(midbottom=(rect.centerx, rect.top - 10 + bob))
        surface.blit(hand, hand_rect)

    def _draw_hint(self, surface):
        if self._hint_timer >= HINT_DURATION:
            return
        if self.zoom <= 1.0:
            return

        if self._font is None:
            self._font = pygame.font.SysFont("comicsansms", max(16, int(self.screen.height * 0.07)))

        remaining = HINT_DURATION - self._hint_timer
        alpha = 255 if remaining > HINT_FADE else int(255 * (remaining / HINT_FADE))

        text_surf = self._font.render(HINT_TEXT, True, (255, 255, 255))
        text_surf.set_alpha(alpha)
        rect = text_surf.get_rect(midtop=(self.screen.width // 2, 16))
        surface.blit(text_surf, rect)

    def _draw_fight_prompt(self, surface):
        node = self.pending_fight_node
        if node is None:
            return

        node_rect = self._node_rects.get(node)
        if node_rect is None:
            return

        box_height = int(self.screen.height * 0.28)
        box_width = int(box_height * (950 / 1200))
        box_image = pygame.transform.smoothscale(self._box_image, (box_width, box_height))


        margin = 10
        gap = int(node_rect.height * 0.15)
        space_above = node_rect.top - gap

        if space_above >= box_height + margin:
            box_rect = box_image.get_rect(midbottom=(node_rect.centerx, node_rect.top - gap))
        else:
            box_rect = box_image.get_rect(midtop=(node_rect.centerx, node_rect.bottom + gap))

        self._clamp_rect_to_screen(box_rect)

        surface.blit(box_image, box_rect)
        self._fight_box_rect = box_rect

        difficulty = get_fight_difficulty(node)
        enemy_team = get_fight_config(node).get("enemy_team", [])

        self._draw_difficulty_hearts(surface, box_rect, difficulty)
        self._draw_enemy_team_preview(surface, box_rect, enemy_team)
        self._draw_fight_button(surface, box_rect)

    def _clamp_rect_to_screen(self, rect, margin=10):
        rect.left = max(margin, min(rect.left, self.screen.width - rect.width - margin))
        rect.top = max(margin, min(rect.top, self.screen.height - rect.height - margin))

    def _draw_difficulty_hearts(self, surface, box_rect, difficulty, total=5):
        heart_size = max(1, int(box_rect.width * 0.14))
        heart_image = pygame.transform.smoothscale(self._full_heart_image, (heart_size, heart_size))

        spacing = heart_size * 1.1
        start_x = box_rect.centerx - spacing * (total - 1) / 2
        y = box_rect.top + box_rect.height * 0.16

        for i in range(total):
            x = start_x + i * spacing
            heart = heart_image.copy()
            if i >= difficulty:
                heart.set_alpha(60)
            rect = heart.get_rect(center=(int(x), int(y)))
            surface.blit(heart, rect)

    def _get_enemy_icon(self, name):
        icon = self._enemy_icon_cache.get(name)
        if icon is None:
            icon = pygame.image.load(f"unit/{name}.png").convert_alpha()
            self._enemy_icon_cache[name] = icon
        return icon

    def _draw_enemy_team_preview(self, surface, box_rect, enemy_team):
        if self._label_font is None:
            self._label_font = pygame.font.SysFont("comicsansms", max(12, int(self.screen.height * 0.033)), bold=True)

        label_surf = self._label_font.render("Enemy Team", True, (0, 0, 0))
        label_y = box_rect.top + box_rect.height * 0.34
        label_rect = label_surf.get_rect(center=(box_rect.centerx, int(label_y)))
        surface.blit(label_surf, label_rect)

        if not enemy_team:
            return

        icon_size = max(1, int(box_rect.width * 0.16))
        spacing = icon_size * 1.15
        start_x = box_rect.centerx - spacing * (len(enemy_team) - 1) / 2
        y = box_rect.top + box_rect.height * 0.56

        for i, name in enumerate(enemy_team):
            icon = pygame.transform.smoothscale(self._get_enemy_icon(name), (icon_size, icon_size))
            x = start_x + i * spacing
            rect = icon.get_rect(center=(int(x), int(y)))
            surface.blit(icon, rect)

    def _draw_fight_button(self, surface, box_rect):
        button_width = int(box_rect.width * 0.85)
        native_w, native_h = self._fight_button_image.get_size()
        button_height = int(button_width * (native_h / native_w)) if native_w else button_width

        button_image = pygame.transform.smoothscale(self._fight_button_image, (button_width, button_height))
        button_rect = button_image.get_rect(midbottom=(box_rect.centerx, box_rect.bottom - int(box_rect.height * 0.08)))

        if button_rect.collidepoint(self._mouse_pos):
            button_image = button_image.copy()
            button_image.fill((45, 45, 45, 0), special_flags=pygame.BLEND_RGB_ADD)

        surface.blit(button_image, button_rect)

        self._fight_button_rect = button_rect


    def _draw_shop_prompt(self, surface):
        node = self.pending_shop_node
        if node is None:
            return

        node_rect = self._node_rects.get(node)
        if node_rect is None:
            return

        box_height = int(self.screen.height * 0.16)
        box_width = int(box_height * 1.6)
        box_image = pygame.transform.smoothscale(self._box_image, (box_width, box_height))

        margin = 10
        gap = int(node_rect.height * 0.15)
        space_above = node_rect.top - gap

        if space_above >= box_height + margin:
            box_rect = box_image.get_rect(midbottom=(node_rect.centerx, node_rect.top - gap))
        else:
            box_rect = box_image.get_rect(midtop=(node_rect.centerx, node_rect.bottom + gap))

        self._clamp_rect_to_screen(box_rect)

        surface.blit(box_image, box_rect)
        self._shop_box_rect = box_rect

        self._draw_shop_button(surface, box_rect)

    def _draw_shop_button(self, surface, box_rect):
        button_width = int(box_rect.width * 0.8)
        native_w, native_h = self._enter_button_image.get_size()
        button_height = int(button_width * (native_h / native_w)) if native_w else button_width

        button_image = pygame.transform.smoothscale(self._enter_button_image, (button_width, button_height))
        button_rect = button_image.get_rect(center=box_rect.center)

        if button_rect.collidepoint(self._mouse_pos):
            button_image = button_image.copy()
            button_image.fill((45, 45, 45, 0), special_flags=pygame.BLEND_RGB_ADD)

        surface.blit(button_image, button_rect)

        self._shop_button_rect = button_rect


    def _draw_upgrade_prompt(self, surface):
        node = self.pending_upgrade_node
        if node is None:
            return

        node_rect = self._node_rects.get(node)
        if node_rect is None:
            return

        box_height = int(self.screen.height * 0.16)
        box_width = int(box_height * 1.6)
        box_image = pygame.transform.smoothscale(self._box_image, (box_width, box_height))

        margin = 10
        gap = int(node_rect.height * 0.15)
        space_above = node_rect.top - gap

        if space_above >= box_height + margin:
            box_rect = box_image.get_rect(midbottom=(node_rect.centerx, node_rect.top - gap))
        else:
            box_rect = box_image.get_rect(midtop=(node_rect.centerx, node_rect.bottom + gap))

        self._clamp_rect_to_screen(box_rect)

        surface.blit(box_image, box_rect)
        self._upgrade_box_rect = box_rect

        self._draw_upgrade_button(surface, box_rect)

    def _draw_upgrade_button(self, surface, box_rect):
        button_width = int(box_rect.width * 0.8)
        native_w, native_h = self._enter_button_image.get_size()
        button_height = int(button_width * (native_h / native_w)) if native_w else button_width

        button_image = pygame.transform.smoothscale(self._enter_button_image, (button_width, button_height))
        button_rect = button_image.get_rect(center=box_rect.center)

        if button_rect.collidepoint(self._mouse_pos):
            button_image = button_image.copy()
            button_image.fill((45, 45, 45, 0), special_flags=pygame.BLEND_RGB_ADD)

        surface.blit(button_image, button_rect)

        self._upgrade_button_rect = button_rect

    def _draw_card_prompt(self, surface):
        node = self.pending_card_node
        if node is None:
            return

        node_rect = self._node_rects.get(node)
        if node_rect is None:
            return

        box_height = int(self.screen.height * 0.16)
        box_width = int(box_height * 1.6)
        box_image = pygame.transform.smoothscale(self._box_image, (box_width, box_height))

        margin = 10
        gap = int(node_rect.height * 0.15)
        space_above = node_rect.top - gap

        if space_above >= box_height + margin:
            box_rect = box_image.get_rect(midbottom=(node_rect.centerx, node_rect.top - gap))
        else:
            box_rect = box_image.get_rect(midtop=(node_rect.centerx, node_rect.bottom + gap))

        self._clamp_rect_to_screen(box_rect)

        surface.blit(box_image, box_rect)
        self._card_box_rect = box_rect

        self._draw_card_button(surface, box_rect)

    def _draw_card_button(self, surface, box_rect):
        button_width = int(box_rect.width * 0.8)
        native_w, native_h = self._enter_button_image.get_size()
        button_height = int(button_width * (native_h / native_w)) if native_w else button_width

        button_image = pygame.transform.smoothscale(self._enter_button_image, (button_width, button_height))
        button_rect = button_image.get_rect(center=box_rect.center)

        if button_rect.collidepoint(self._mouse_pos):
            button_image = button_image.copy()
            button_image.fill((45, 45, 45, 0), special_flags=pygame.BLEND_RGB_ADD)

        surface.blit(button_image, button_rect)

        self._card_button_rect = button_rect


def gen_map(screen, seed, zoom=MAP_ZOOM):
    w, h = screen.width * zoom, screen.height * zoom

    def col_x(i, total_cols):
        return w * (0.08 + i * (0.84 / (total_cols - 1)))

    def col_y_positions(count):
        if count == 1:
            return [h * 0.5]
        margin = 0.05

        #step = (1-2 * margin)/(count-1)
        #return[h * (margin + i*step) for i in range(count)]

        step = (1 - 2 * margin) / count
        return [h * (margin + step * (i + 0.5)) for i in range(count)]


    node_size = h * 0.11
    preferred_spacing = node_size * 1.8   
    hard_min_spacing = node_size * 1.15   

    def place_node(base_x, base_y, max_x_jitter, max_y_jitter, placed_positions):
        for shrink in (1.0, 0.6, 0.3):
            for _ in range(40):
                x = base_x + random.uniform(-max_x_jitter, max_x_jitter) * shrink
                y = base_y + random.uniform(-max_y_jitter, max_y_jitter) * shrink
                if all(math.hypot(x - px, y - py) >= preferred_spacing for px, py in placed_positions):
                    return x, y

        for shrink in (1.0, 0.6, 0.3, 0.0):
            for _ in range(40):
                x = base_x + random.uniform(-max_x_jitter, max_x_jitter) * shrink
                y = base_y + random.uniform(-max_y_jitter, max_y_jitter) * shrink
                if all(math.hypot(x - px, y - py) >= hard_min_spacing for px, py in placed_positions):
                    return x, y

        x, y = base_x, base_y
        for _ in range(20):
            nearest = min(placed_positions, key=lambda p: math.hypot(x - p[0], y - p[1]), default=None)
            if nearest is None:
                break
            dist = math.hypot(x - nearest[0], y - nearest[1])
            if dist >= hard_min_spacing:
                break
            dx, dy = x - nearest[0], y - nearest[1]
            if dist == 0:
                dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
                dist = math.hypot(dx, dy) or 1
            push = (hard_min_spacing - dist) + 1
            x += dx / dist * push
            y += dy / dist * push
        return x, y


    odds = {
    "upgrade": 90, #10 Percent
    "shop": 70, #20 Percent
    "card": 50, # 20 Percent
    "combat": 0} #50 Percent


    random.seed(seed)

    nodes_per_column = [1]

    length = random.randint(7, 8)

    for i in range(length):

        progress = i / (length-3)

        if progress < .25:
            minL = 2
            maxL = 4
        elif progress < .75:
            minL = 3
            maxL = 5
        elif progress < .9:
            minL = 3
            maxL = 5
        else:
            minL = 1
            maxL = 2



        prev = nodes_per_column[-1]

        candidates = [c for c in (prev - 1, prev, prev + 1) if c >= 1]

        within_range = [c for c in candidates if minL <= c <= maxL]

        if within_range:
            count = random.choice(within_range)
        elif prev < minL:
            count = prev + 1
        elif prev > maxL:
            count = prev - 1
        else:
            count = prev

        nodes_per_column.append(count)

    length += 2

    start = MapNode("start", col_x(0, length), h * 0.5)
    boss = MapNode("boss", col_x(length - 1, length), h * 0.5)

    columns = [[start]]
    placed_positions = [(start.x, start.y), (boss.x, boss.y)]

    col_spacing = w * (0.84 / (length - 1))
    max_x_jitter = col_spacing * 0.30

    for column_index in range(1, length - 1):

        def roll_card_type():
            randint = random.randint(0, 100)
            for key in odds.keys():
                if randint > odds[key]:
                    return key
            return "combat"

        node_count = nodes_per_column[column_index]
        base_x = col_x(column_index, length)
        base_ys = col_y_positions(node_count)

        margin = 0.05
        step = (1 - 2 * margin) / node_count if node_count > 1 else 1.0
        max_y_jitter = h * step * 0.35

        column = []
        for base_y in base_ys:
            x, y = place_node(base_x, base_y, max_x_jitter, max_y_jitter, placed_positions)
            placed_positions.append((x, y))
            column.append(MapNode(roll_card_type(), x, y))
        columns.append(column)


    columns.append([boss])

    node_to_col = {node: i for i, column in enumerate(columns) for node in column}

    max_adjacent_connect_dist = h * 0.35

    for i, column in enumerate(columns):
        for node in column:

            if i < len(columns) - 1:
                closest = None
                closest_dist = 999999
                for node_other in columns[i + 1]:
                    if abs(node.y - node_other.y) < closest_dist:
                        closest_dist = abs(node.y - node_other.y)
                        closest = node_other

            node.connect(closest)


    nodes_with_no_connection = set(node for column in columns for node in column if node != start)
    for i, column in enumerate(columns):
        for node in column:
            nodes_with_no_connection = nodes_with_no_connection-node.connections


    #Heh time to conenct 
    for node in nodes_with_no_connection:
        nearest_node = None
        node_dist = 99999999

        prev_column = columns[node_to_col[node] - 1]

        for node_other in prev_column:
            if node == node_other:
                continue

            dist = math.sqrt((node_other.x - node.x) ** 2 + (node_other.y - node.y) ** 2)
            if dist < node_dist:
                node_dist = dist
                nearest_node = node_other


        if nearest_node is not None:
            nearest_node.connect(node)

                         



    #More node shit connections
    nodes = [node for column in columns for node in column if node.node_type not in ["start", "boss"]]

    for i in range(8):
        selected_node = random.choice(nodes)

        connected_nodes = selected_node.connections

        col_i = node_to_col[selected_node]
        if col_i + 1 >= len(columns):
            continue

        next_column = columns[col_i + 1]

        nearest_node = None
        nearest_dist = 99999999999

        for node in next_column:
            if node == selected_node or node in connected_nodes or node.node_type == "boss":
                continue

            dist = math.sqrt((selected_node.x - node.x) ** 2 + (selected_node.y - node.y) ** 2)
            if dist < nearest_dist and dist <= max_adjacent_connect_dist:
                nearest_dist = dist
                nearest_node = node

        if nearest_node != None:
            selected_node.connect(nearest_node)

    score = {
        "upgrade": 3,
        "shop": 5,
        "card": 3,
        "combat": -2,
        "start": 0,
        "boss": 0
    }




    def find_all_paths(node, current_path, all_paths):

        current_path.append(node)

        if node.node_type == "boss":
            all_paths.append(current_path.copy())

        else:
            for next_node in node.connections:
                find_all_paths(next_node, current_path, all_paths)

        current_path.pop()


    all_paths = []

    find_all_paths(start, [], all_paths)




    def get_path_rankings():
        path_rankings = {}
        for i, path in enumerate(all_paths):
            path_rankings[i] = sum(
                score[node.node_type]
                for node in path
            )
        return path_rankings




    def get_map_badness(rankings):
        badness = 0

        for ranking in rankings.values():

            if ranking < -1:
                badness += abs(ranking + 1)
            elif ranking > 1:
                badness += ranking - 1

        return badness

    nodes = [node for column in columns for node in column if node.node_type not in ["start", "boss"]]




    max_iterations = 100

    for iteration in range(max_iterations):
        rankings = get_path_rankings()
        current_badness = get_map_badness(rankings)

        if current_badness == 0:
            break

        best_node = None
        best_type = None
        best_badness = current_badness

        possible_types = ["upgrade", "shop", "card", "combat"]

        for node in nodes:
            old_type = node.node_type
            for new_type in possible_types:

                if new_type == old_type:
                    continue

                node.switch_node_type(new_type)
                new_rankings = get_path_rankings()
                new_badness = get_map_badness(new_rankings)

                if new_badness < best_badness:

                    best_badness = new_badness
                    best_node = node
                    best_type = new_type

                node.switch_node_type(old_type)



        if best_node is None: break


        best_node.switch_node_type(best_type)


    else:

        print("failed")


    nodes = [node for column in columns for node in column]



    for node in nodes:
        node.x /= w
        node.y /= h

    return nodes, start, iteration


def build_example_map(screen):
    w, h = screen.width, screen.height

    def col_x(i, total_cols):
        return w * (0.08 + i * (0.84 / (total_cols - 1)))

    start = MapNode("card", col_x(0, 7), h * 0.5)

    n1 = MapNode("combat", col_x(1, 7), h * 0.3)
    n1b = MapNode("upgrade", col_x(1, 7), h * 0.75)

    n2a = MapNode("card", col_x(2, 7), h * 0.18)
    n2b = MapNode("shop", col_x(2, 7), h * 0.45)
    n2c = MapNode("upgrade", col_x(2, 7), h * 0.82)

    n3a = MapNode("upgrade", col_x(3, 7), h * 0.18)
    n3b = MapNode("upgrade", col_x(3, 7), h * 0.45)
    n3c = MapNode("upgrade", col_x(3, 7), h * 0.82)

    n4a = MapNode("upgrade", col_x(4, 7), h * 0.18)
    n4b = MapNode("card", col_x(4, 7), h * 0.45)
    n4c = MapNode("combat", col_x(4, 7), h * 0.82)

    n5a = MapNode("shop", col_x(5, 7), h * 0.3)
    n5b = MapNode("card", col_x(5, 7), h * 0.75)

    boss = MapNode("boss", col_x(6, 7), h * 0.5)

    start.connect(n1)
    start.connect(n1b)

    n1.connect(n2a)
    n1.connect(n2b)
    n1b.connect(n2b)
    n1b.connect(n2c)

    n2a.connect(n3a)
    n2b.connect(n3b)
    n2b.connect(n3c)
    n2c.connect(n3c)

    n3a.connect(n4a)
    n3b.connect(n4b)
    n3c.connect(n4c)

    n4a.connect(n5a)
    n4b.connect(n5a)
    n4c.connect(n5b)

    n5a.connect(boss)
    n5b.connect(boss)

    nodes = [start, n1, n1b, n2a, n2b, n2c, n3a, n3b, n3c,
             n4a, n4b, n4c, n5a, n5b, boss]

    for node in nodes:
        node.x /= w
        node.y /= h

    return nodes, start