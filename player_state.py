import random

from card import CARD_NAMES
from units import spawn_unit


STARTING_TEAM = ["spacecat", "nevada", "booch todd", "snog"]

DECK_SIZE = 10

DEFAULT_CARD_POOL = {
    "explosion": 5,
    "field": 5,
    "hospital": 5,
    "lazer": 5,
    "ace": 5,
    "disk": 5,
    "carder": 5,
    "cuck": 5,
    "dragon": 5,
    "horse": 5
}


class PlayerState:
    def __init__(self, team_names=None, card_pool=None):
        self.team_names = team_names if team_names is not None else list(STARTING_TEAM)
        self.card_pool = dict(card_pool) if card_pool is not None else dict(DEFAULT_CARD_POOL)
        self.unit_decks = {name: [] for name in self.team_names}
        self._fill_starting_decks()

    def _fill_starting_decks(self):
        for name in self.team_names:
            deck = self.unit_decks[name]
            while len(deck) < DECK_SIZE:
                choices = [
                    c for c in CARD_NAMES
                    if self.available_count(c, exclude_unit=name) - deck.count(c) > 0
                ]
                if not choices:
                    break
                deck.append(random.choice(choices))

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

    def build_team(self):
        return [spawn_unit(name, deck=self.unit_decks.get(name)) for name in self.team_names]