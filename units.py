import pygame
from effects import *
from card import CARD_NAMES, create_card
from visual_effects import spawn_passive_effect
import math
import random


class Passive:
    def __init__(self, trigger, effects=None, cost=None):
        self.trigger = trigger
        self.effects = effects if effects is not None else []
        self.cost = cost if cost is not None else [Cost()]

    def can_activate(self, game, unit):
        return all(cost.can_pay(game, unit) for cost in self.cost)

    def activate(self, game, unit, target=None):
        for cost in self.cost:
            cost.pay(game, unit)

        for effect in self.effects:
            effect.apply(game, unit, source=unit, target=target)


UNIT_STATS = {
    "blob": {
        "health": 100,
        "passives": [Passive(Trigger.ON_TURN_START, effects=[HealEffect(10)])],
    },
    "frog": {
        "health": 60,
        "passives": [Passive(Trigger.ON_ATTACK, effects=[DrawEffect(1)])],
    },
    "penguin": {
        "health": 70,
        "passives": [Passive(Trigger.ON_DEATH, effects=[HealTeamEffect(20)])],
    },
    "spacecat": {
        "health": 60,
        "passives": [Passive(Trigger.ON_PLAY, effects=[HealEffect(10)])],
    },
    "demon": {
        "health": 20,
        "passives": [Passive(Trigger.ON_DEATH, effects=[DamageEffect(10)])],
    },
    "nevada": {
        "health": 30,
        "passives": [Passive(Trigger.ON_TURN_START, effects=[DrawEffect(1)])],
    },
    "snog": {
        "health": 120,
        "passives": [Passive(Trigger.ON_TURN_START, effects=[HealEffect(10)])],
    },
    "booch todd": {
        "health": 200,
        "passives": [Passive(Trigger.ON_TURN_START, effects=[DrawEffect(2)])],
    },
    "constitution": {
        "health": 40,
        "passives": [Passive(Trigger.ON_TURN_START, effects=[DrawEffect(3)])],
    },
    "weenus fungel": {
        "health": 40,
        "passives": [Passive(Trigger.ON_PLAY, effects=[DrawEffect(1)])],
    }


}


UNIT_POWER = {
    "blob": 5,
    "frog": 8,
    "penguin": 6,
    "spacecat": 5,
    "nevada": 7,
    "snog": 6,
    "booch todd": 10,
    "constitution" : 5,
    "demon": 2,
    "weenus fungel": 4,
}

UNIT_SHOP_POOL = ["blob", "frog", "penguin", "nevada", "snog", "booch todd", "constitution", "weenus fungel"]

ENEMY_UNIT_POOL = list(UNIT_POWER.keys())


def get_unit_power(name):
    return UNIT_POWER.get(name, 5)

UNIT_PRICE_MIN = 150
UNIT_PRICE_MAX = 300
UNIT_POWER_MIN = 1
UNIT_POWER_MAX = 10


def get_unit_price(name):
    power = UNIT_POWER.get(name, 5)
    frac = (power - UNIT_POWER_MIN) / (UNIT_POWER_MAX - UNIT_POWER_MIN)
    price = UNIT_PRICE_MIN + frac * (UNIT_PRICE_MAX - UNIT_PRICE_MIN)
    return int(round(price / 10) * 10)


def random_deck():
    #return [create_card("hospital") for _ in range(10)]
    return [create_card(random.choice(CARD_NAMES)) for _ in range(10)]

def spawn_unit(name, controller=None, deck=None):
    stats = UNIT_STATS.get(name, {"health": 1, "passives": None})
    unit = Unit(name=name, health=stats["health"], passives=stats["passives"], controller=controller)
    if deck:
        unit.deck = [create_card(card_name) for card_name in deck]
    else:
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
        self.used_cards = []

        self._image = None
        self.full_heart = pygame.image.load("assets/full_heart.png").convert_alpha()
        self.half_heart = pygame.image.load("assets/half_heart.png").convert_alpha()
        self.tombstone_image = pygame.image.load("assets/tombstone.png").convert_alpha()
        self.back_of_card = pygame.image.load("assets/card_back.png").convert_alpha()
        self.shield_image = pygame.image.load("assets/shield.png").convert_alpha()
        self.stretch_x = 1.0
        self.stretch_y = 1.0
        self.internal_timer = 0
        self.flash_timer = 0
        self.damage_amount = 0
        self.draw_animations = []
        self._pending_draw_delay = 0.0

        self.reshuffle_timer = 0.0
        self.reshuffle_duration = 0.6
        self.pending_reshuffle_draws = 0

        self.extra_draw_count = 0
        self.glass_cannon = False
        self.vision = 0

        self.statuses = {}

        self._image_scale_cache = None
        self._tombstone_scale_cache = None
        self._card_back_scale_cache = None
        self._full_heart_scale_cache = None
        self._half_heart_scale_cache = None
        self._poison_tint_cache = None
        self._shield_scale_cache = None

    def _scaled(self, image, w, h, cache_attr):
        cache = getattr(self, cache_attr)
        if cache is not None and cache[0] == (w, h):
            return cache[1]
        scaled = pygame.transform.smoothscale(image, (w, h))
        setattr(self, cache_attr, ((w, h), scaled))
        return scaled

    def _poison_tinted(self, image):
        key = (image.get_width(), image.get_height())
        cache = self._poison_tint_cache
        if cache is not None and cache[0] == key:
            return cache[1]
        tinted = image.copy()
        tinted.fill((150, 90, 210), special_flags=pygame.BLEND_RGB_MULT)
        self._poison_tint_cache = (key, tinted)
        return tinted

    def _scaled_shield(self, w, h):
        cache = self._shield_scale_cache
        if cache is not None and cache[0] == (w, h):
            return cache[1]
        scaled = pygame.transform.smoothscale(self.shield_image, (w, h))
        scaled.set_alpha(170)
        self._shield_scale_cache = ((w, h), scaled)
        return scaled

    def _draw_weakened(self, surface, image, rect):
        strip_count = 8
        strip_h = max(1, rect.height // strip_count)
        t = self.internal_timer * 0.2
        amplitude = max(1, rect.width * 0.035)

        y = 0
        i = 0
        while y < rect.height:
            h = min(strip_h, rect.height - y)
            offset = int(math.sin(t + i * 1.1) * amplitude)
            strip = image.subsurface(pygame.Rect(0, y, rect.width, h))
            surface.blit(strip, (rect.x + offset, rect.y + y))
            y += h
            i += 1

    def get_image(self):
        if self._image is None:
            self._image = pygame.image.load(f"unit/{self.name}.png").convert_alpha()
        return self._image

    @property
    def is_dead(self):
        return self.health <= 0

    def _heart_units(self, hp):
        return int(max(0, hp) // 10)

    def draw(self, surface, x, y, size, left):
        if self.is_dead:
            w = max(1, int(size))
            h = max(1, int(size))
            image = self._scaled(self.tombstone_image, w, h, "_tombstone_scale_cache")
            rect = image.get_rect(center=(x, y))
            surface.blit(image, rect)
            return

        w = max(1, int(size * self.stretch_x))
        h = max(1, int(size * self.stretch_y))

        rw = max(1, 2 * round(w / 2))
        rh = max(1, 2 * round(h / 2))
        image = self._scaled(self.get_image(), rw, rh, "_image_scale_cache")
        rect = image.get_rect(center=(x, y))

        draw_image = image
        if self.statuses.get("poison", 0) > 0:
            draw_image = self._poison_tinted(draw_image)

        if self.statuses.get("weaken", 0) > 0:
            self._draw_weakened(surface, draw_image, rect)
        else:
            surface.blit(draw_image, rect)

        if self.statuses.get("shield", 0) > 0:
            shield_image = self._scaled_shield(rect.width, rect.height)
            surface.blit(shield_image, rect)


        #Back Of Cards
        cb_w = max(1, int(size*.75))
        cb_h = max(1, int(size*1))
        card_back_image = self._scaled(self.back_of_card, cb_w, cb_h, "_card_back_scale_cache")


        for i, card in enumerate(self.deck[::-1]):

            image = card_back_image
            rect = image.get_rect(center=(x, y))
            if not left:
                rect.centerx = (x+surface.get_width()+i*25)//2 
            else:
                rect.centerx = (x-i*25)//2


            #Vision bonus
            if len(self.deck) - i <= self.vision:
                image = pygame.transform.scale(card.get_image(), (cb_w, cb_h))
                surface.blit(image, rect)


            surface.blit(image, rect)

        deck_x = (x - 0) // 2 if left else (x + surface.get_width() + 0) // 2
        deck_y = y

        if self.reshuffle_timer > 0:
            shuffle_t = 1 - (self.reshuffle_timer / self.reshuffle_duration)
            wobble = math.sin(shuffle_t * math.pi * 8)
            jitter_x = wobble * 10
            jitter_y = abs(math.sin(shuffle_t * math.pi * 4)) * 6
            angle = wobble * 18

            shuffled_image = pygame.transform.rotate(card_back_image, angle)
            rect1 = shuffled_image.get_rect(center=(deck_x + jitter_x, deck_y - jitter_y))
            surface.blit(shuffled_image, rect1)

            shuffled_image2 = pygame.transform.rotate(card_back_image, -angle)
            rect2 = shuffled_image2.get_rect(center=(deck_x - jitter_x * 0.7, deck_y + jitter_y * 0.7))
            surface.blit(shuffled_image2, rect2)



        #Used Cards

        for i, card in enumerate(self.used_cards):

            image = pygame.transform.scale(card.get_image(), (cb_w, cb_h))
            rect = image.get_rect(center=(x, y))
            if left:
                rect.centerx = (x*1.5+i*10)
            else:
                rect.centerx = (x*.85-i*10)
            surface.blit(image, rect)



        for anim in self.draw_animations:
            if anim["elapsed"] < 0:
                continue
            t = min(1.0, anim["elapsed"] / anim["duration"]) if anim["duration"] else 1.0
            ease = 1 - (1 - t) ** 3
            hand_x = x
            hand_y = y 
            cur_x = deck_x + (hand_x - deck_x) * ease
            cur_y = deck_y + (hand_y - deck_y) * ease
            travel_image = card_back_image.copy()
            travel_image.set_alpha(int(255 * ease))
            rect = travel_image.get_rect(center=(cur_x, cur_y))
            surface.blit(travel_image, rect)




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

        heart_size = max(1, int(size))
        full_heart_scaled = self._scaled(self.full_heart, heart_size, heart_size, "_full_heart_scale_cache")
        half_heart_scaled = self._scaled(self.half_heart, heart_size, heart_size, "_half_heart_scale_cache")

        for i in range(full_hearts):
            offset = base_offset + size * i * .5
            rect = full_heart_scaled.get_rect(center=(x - direction * offset, y))
            surface.blit(full_heart_scaled, rect)

        if full_hearts_flash:
            flash_full_heart = full_heart_scaled.copy()
            flash_full_heart.set_alpha(int(self.flash_timer / 120 * 255))
            for i in range(full_hearts_flash):
                offset = base_offset + size * (full_hearts + i) * .5
                rect = flash_full_heart.get_rect(center=(x - direction * offset, y))
                surface.blit(flash_full_heart, rect)

        for i in range(half_hearts):
            offset = base_offset + size * (full_hearts + full_hearts_flash + i) * .5
            rect = half_heart_scaled.get_rect(center=(x - direction * offset, y))
            surface.blit(half_heart_scaled, rect)

        if half_hearts_flash:
            flash_half_heart = half_heart_scaled.copy()
            flash_half_heart.set_alpha(int(self.flash_timer / 120 * 255))
            for i in range(half_hearts_flash):
                offset = base_offset + size * (full_hearts + full_hearts_flash + half_hearts + i) * .5
                rect = flash_half_heart.get_rect(center=(x - direction * offset, y))
                surface.blit(flash_half_heart, rect)



    def update(self, clock, game=None):
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

        if self.reshuffle_timer > 0:
            self.reshuffle_timer -= dt
            if self.reshuffle_timer <= 0:
                self.reshuffle_timer = 0.0
                draws = self.pending_reshuffle_draws
                self.pending_reshuffle_draws = 0
                for _ in range(draws):
                    self.draw_card(game)

        self._check_reshuffle()

    def _check_reshuffle(self):
        if self.is_dead:
            return
        if self.reshuffle_timer > 0 or self.pending_reshuffle_draws > 0:
            return
        if not self.hand and not self.deck and self.used_cards:
            random.shuffle(self.used_cards)
            self.deck = self.used_cards
            self.used_cards = []
            self.reshuffle_timer = self.reshuffle_duration
            self.pending_reshuffle_draws = 2

    def add_status(self, status_name, amount=1):
        if self.is_dead:
            return
        self.statuses[status_name] = self.statuses.get(status_name, 0) + amount

    def get_status(self, status_name):
        return self.statuses.get(status_name, 0)

    def tick_statuses(self, game=None):
        """Called once at the start of this unit's team's turn."""
        if self.is_dead:
            return

        poison = self.statuses.get("poison", 0)
        if poison > 0:
            self.take_damage(poison, game, source=None)
            remaining = self.statuses.get("poison", 0) - 1
            if remaining <= 0:
                self.statuses.pop("poison", None)
            else:
                self.statuses["poison"] = remaining

        weaken = self.statuses.get("weaken", 0)
        if weaken > 0:
            remaining = weaken - 1
            if remaining <= 0:
                self.statuses.pop("weaken", None)
            else:
                self.statuses["weaken"] = remaining

        shield = self.statuses.get("shield", 0)
        if shield > 0:
            remaining = shield - 1
            if remaining <= 0:
                self.statuses.pop("shield", None)
            else:
                self.statuses["shield"] = remaining

    def _round_to_ten(self, amount):
        if amount <= 0:
            return 0
        return max(10, int((amount + 5) // 10) * 10)

    def take_damage(self, amount, game=None, source=None):
        if self.is_dead:
            return

        if self.statuses.get("weaken", 0) > 0:
            amount = amount * 1.5

        if self.statuses.get("shield", 0) > 0:
            amount = amount // 2

        amount = self._round_to_ten(amount)

        self.health -= amount
        self.flash_timer = 120
        self.damage_amount = amount

        if self.is_dead and game is not None:
            self.trigger_passives(game, Trigger.ON_DEATH, target=source)

    def trigger_passives(self, game, trigger, target=None):
        if self.is_dead and trigger != Trigger.ON_DEATH:
            return

        actual_target = target if target is not None else self

        for passive in self.passives:
            if passive.trigger != trigger:
                continue
            if not passive.can_activate(game, self):
                continue
            passive.activate(game, self, target=actual_target)
            spawn_passive_effect(game, self, trigger, actual_target)

    def heal(self, amount):
        if self.is_dead:
            return
        self.health = min(self.max_health, self.health + amount)


    def apply_upgrades(self, extra_heart=0, extra_card=0, glass_cannon=False, vision=0):
        self.max_health += 20 * extra_heart
        self.extra_draw_count = extra_card
        self.vision = vision
        if glass_cannon:
            self.glass_cannon = True
            self.max_health = max(1, int(self.max_health / 2))
        self.health = self.max_health

    def draw_card(self, game=None):
        if self.is_dead:
            return
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