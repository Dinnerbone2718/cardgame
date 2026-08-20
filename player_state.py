import random

from card import CARD_NAMES
from units import spawn_unit


STARTING_TEAM = ["spacecat", "booch todd", "weenus fungel", "snog"] 

DECK_SIZE = 10

EXTRA_HEART_AMOUNT = 20

DEFAULT_CARD_POOL = {
    "explosion": 10,
    "field": 10,
    "hospital": 10,
    "lazer": 10,
    "ace": 10,
    "disk": 10,
    "carder": 10,
    "cuck": 10,
    "dragon": 10,
    "horse": 10,
    "fartman": 10,
    "donghuahorse": 10,
    "cuck_friendship": 10,
    "fox": 10,
    "yogurt":10,
    "marmalade_peanut": 10,
    "blorpit": 10,
    "gronkle": 10,
    "shield": 10,
    "genuis": 10
}


class PlayerState:
    def __init__(self, team_names=None, card_pool=None, coins=10):
        self.team_names = team_names if team_names is not None else list(STARTING_TEAM)
        self.card_pool = dict(card_pool) if card_pool is not None else dict(DEFAULT_CARD_POOL)
        self.unit_decks = {name: [] for name in self.team_names}
        self.unit_upgrades = {name: self._default_upgrades() for name in self.team_names}
        self.coins = coins
        self._fill_starting_decks()

    def _default_upgrades(self):
        return {"extra_heart": 0, "extra_card": 0, "glass_cannon": False, "vision": 0}

    def get_upgrades(self, unit_name):
        if unit_name not in self.unit_upgrades:
            self.unit_upgrades[unit_name] = self._default_upgrades()
        return self.unit_upgrades[unit_name]

    def eligible_units_for_upgrade(self, upgrade_type):
        if upgrade_type == "glass_cannon":
            return [name for name in self.team_names if not self.get_upgrades(name)["glass_cannon"]]
        return list(self.team_names)

    def apply_upgrade(self, unit_name, upgrade_type):
        upgrades = self.get_upgrades(unit_name)
        if upgrade_type == "glass_cannon":
            upgrades["glass_cannon"] = True
        else:
            upgrades[upgrade_type] += 1

    def add_coins(self, amount):
        self.coins += amount

    def spend_coins(self, amount):
        if self.coins < amount:
            return False
        self.coins -= amount
        return True

    def _fill_starting_decks(self):
        for name in self.team_names:
            self._fill_deck(name)

    def cards_used_elsewhere(self, exclude_unit=None):
        used = {}
        for unit_name, deck in self.unit_decks.items():
            if unit_name == exclude_unit:
                continue
            for card_name in deck:
                used[card_name] = used.get(card_name, 0) + 1
        return used

    def available_count(self, card_name, exclude_unit=None):
        total = self.card_pool.get(card_name, 0)
        used = self.cards_used_elsewhere(exclude_unit).get(card_name, 0)
        return total - used

    def is_deck_valid(self, unit_name):
        return len(self.unit_decks.get(unit_name, [])) == DECK_SIZE

    def add_to_pool(self, card_name, amount=1):
        self.card_pool[card_name] = self.card_pool.get(card_name, 0) + amount

    def replace_team_unit(self, index, new_unit_name):
        if index < 0 or index >= len(self.team_names):
            return False
        self.team_names[index] = new_unit_name
        if new_unit_name not in self.unit_decks:
            self.unit_decks[new_unit_name] = []
        self.get_upgrades(new_unit_name)
        self._fill_deck(new_unit_name)
        return True

    def _fill_deck(self, name):
        deck = self.unit_decks[name]
        while len(deck) < DECK_SIZE:
            choices = [
                c for c in CARD_NAMES
                if self.available_count(c, exclude_unit=name) - deck.count(c) > 0
            ]
            if not choices:
                break
            deck.append(random.choice(choices))

    def build_team(self):
        units = []
        for name in self.team_names:
            unit = spawn_unit(name, deck=self.unit_decks.get(name))
            upgrades = self.get_upgrades(name)
            unit.apply_upgrades(
                extra_heart=upgrades["extra_heart"],
                extra_card=upgrades["extra_card"],
                glass_cannon=upgrades["glass_cannon"],
                vision=upgrades["vision"]
            )
            units.append(unit)
        return units