from enum import Enum
import pygame
from effects import Cost
from card import CARD_NAMES, create_card
import math
import random

class Trigger(Enum):
    ON_PLAY = "on_play"
    ON_ATTACK = "on_attack"
    ON_DEATH = "on_death"
    ON_TURN_START = "on_turn_start"


class Passive:
    def __init__(self, trigger, effects=None, cost=None):
        self.trigger = trigger
        self.effects = effects if effects is not None else []
        self.cost = cost if cost is not None else [Cost()]

    def can_activate(self, game, unit):
        return all(cost.can_pay(game, unit.controller) for cost in self.cost)

    def activate(self, game, unit, target=None):
        for cost in self.cost:
            cost.pay(game, unit.controller)

        for effect in self.effects:
            effect.apply(game, unit.controller, source=unit, target=target)


UNIT_STATS = {
    "blob": {"health": 100, "passives": None},
    "frog": {"health": 60, "passives": None},
    "penguin": {"health": 70, "passives": None},
    "spacecat": {"health": 60, "passives": None},
    "demon": {"health": 20, "passives": None},
}


def random_deck():

    return [create_card(random.choice(CARD_NAMES)) for _ in range(10)]


def spawn_unit(name, controller=None):
    stats = UNIT_STATS.get(name, {"health": 1, "passives": None})
    unit = Unit(name=name, health=stats["health"], passives=stats["passives"], controller=controller)
    unit.deck = random_deck()
    unit.hand.extend(unit.deck[:5])
    del unit.deck[:5]

    return unit


class Unit:
    def __init__(self, name="default", health=1, passives=None, controller=None):
        self.name = name
        self.health = health
        self.max_health = health
        self.passives = passives if passives is not None else []
        self.controller = controller
        self.hand = []
        self.deck = []

        self._image = None
        self.full_heart = pygame.image.load("assets/full_heart.png").convert_alpha()
        self.half_heart = pygame.image.load("assets/half_heart.png").convert_alpha()
        self.stretch_x = 1.0
        self.stretch_y = 1.0
        self.internal_timer = 0
        self.flash_timer = 0
        self.damage_amount = 0
        self.draw_animations = []
        self._pending_draw_delay = 0.0


    def get_image(self):
        if self._image is None:
            self._image = pygame.image.load(f"unit/{self.name}.png").convert_alpha()
        return self._image

    def _heart_units(self, hp):
        return int(max(0, hp) // 10)

    def draw(self, surface, x, y, size, left):
        w = max(1, int(size * self.stretch_x))
        h = max(1, int(size * self.stretch_y))
        image = pygame.transform.smoothscale(self.get_image(), (w, h))
        rect = image.get_rect(center=(x, y))
        surface.blit(image, rect)


        size *= .25
        
        prev_health = self.health + self.damage_amount
        prev_units = self._heart_units(prev_health)
        cur_units = self._heart_units(self.health)
        lost_units = max(0, prev_units - cur_units)

        full_hearts = cur_units // 2
        half_hearts = cur_units % 2

        full_hearts_flash = lost_units // 2
        half_hearts_flash = lost_units % 2

        if self.health <= 0 and self.flash_timer <= 0:
            return


        direction = (int(left) * 2 - 1)
        base_offset = size * 1.5 

        a = 0
        b = 0
        c = 0
        d = 0

        for i in range(full_hearts):
            full_heart_image = pygame.transform.smoothscale(self.full_heart, (size, size))
            offset = base_offset + size * i * .5
            rect = full_heart_image.get_rect(center=(x - direction * offset, y))
            surface.blit(full_heart_image, rect)

        for i in range(full_hearts_flash):
            full_heart_image = pygame.transform.smoothscale(self.full_heart, (size, size))
            full_heart_image.set_alpha(int(self.flash_timer / 120 * 255))
            offset = base_offset + size * (full_hearts + i) * .5
            rect = full_heart_image.get_rect(center=(x - direction * offset, y))
            surface.blit(full_heart_image, rect)

        for i in range(half_hearts):
            half_heart_image = pygame.transform.smoothscale(self.half_heart, (size, size))
            offset = base_offset + size * (full_hearts + full_hearts_flash + i) * .5
            rect = half_heart_image.get_rect(center=(x - direction * offset, y))
            surface.blit(half_heart_image, rect)

        for i in range(half_hearts_flash):
            half_heart_image = pygame.transform.smoothscale(self.half_heart, (size, size))
            half_heart_image.set_alpha(int(self.flash_timer / 120 * 255))
            offset = base_offset + size * (full_hearts + full_hearts_flash + half_hearts + i) * .5
            rect = half_heart_image.get_rect(center=(x - direction * offset, y))
            surface.blit(half_heart_image, rect)



    def update(self, clock):
        self.internal_timer += 1
        t = self.internal_timer / 12  

        wave = math.sin(t)
        punch = math.copysign(abs(wave) ** 0.5, wave)

        self.stretch_y = 1 + 0.08 * punch 
        self.stretch_x = 1 - 0.01 * punch  

        self.flash_timer-=1
        if self.flash_timer <=0:
            self.flash_timer = 0
            self.damage_amount = 0

        dt = clock.get_time() / 1000
        for anim in self.draw_animations:
            anim["elapsed"] += dt
        self.draw_animations = [a for a in self.draw_animations if a["elapsed"] < a["duration"]]
        if not self.draw_animations:
            self._pending_draw_delay = 0.0

    def take_damage(self, amount):
        self.health -= amount
        self.flash_timer = 120
        self.damage_amount = amount



    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)


    def draw_card(self, game=None):
        if self.deck:
            card = self.deck.pop(0)
            self.hand.append(card)
            duration = 0.35
            self.draw_animations.append({
                "card": card,
                "elapsed": -self._pending_draw_delay,
                "duration": duration,
            })
            self._pending_draw_delay += duration