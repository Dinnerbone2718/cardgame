import pygame

from effects import (
    Cost,
    DamageEffect,
    HealEffect,
    DrawEffect,
    HealTeamEffect,
    HealAllEffect,
    DrawTeamEffect,
    SelfDiscardCost,
)
from visual_effects import spawn_card_effect


CARD_NAMES = ["explosion", "field", "hospital", "lazer", "ace", "disk", "carder"]


def create_card(name):
    builder = _CARD_BUILDERS.get(name)
    if builder is None:
        return TurnCard(name=name, cost=None, requires_target=False, effects=None)
    return builder()


class TurnCard:
    def __init__(self, name="default", cost=None, requires_target=False, effects=None, targeted_effects=None):
        self.name = name
        self.cost = cost if cost is not None else [Cost()]
        self.requires_target = requires_target
        self.effects = effects if effects is not None else []
        self.targeted_effects = targeted_effects if targeted_effects is not None else []

    def get_image(self):
        if not hasattr(self, "_image") or self._image is None:
            self._image = pygame.image.load(f"turn/{self.name}.png").convert_alpha()
        return self._image

    def can_play(self, game, player):
        return all(cost.can_pay(game, player) for cost in self.cost)

    def play(self, game, player, target=None, targets=None):
        for cost in self.cost:
            if not getattr(cost, "interactive", False):
                cost.pay(game, player)

        for effect in self.effects:
            effect.apply(game, player, source=player, target=player)
            spawn_card_effect(game, self.name, player, player)

        if targets is None:
            targets = [target] if target is not None else []

        for (team, effect), chosen_target in zip(self.targeted_effects, targets):
            effect.apply(game, player, source=player, target=chosen_target)
            spawn_card_effect(game, self.name, player, chosen_target)


_CARD_BUILDERS = {
    "explosion": lambda: TurnCard(
        name="explosion",
        requires_target=True,
        targeted_effects=[("enemy", DamageEffect(50)), ("ally", DamageEffect(20))],
    ),
    "field": lambda: TurnCard(
        name="field",
        effects=[HealEffect(40)],
    ),
    "hospital": lambda: TurnCard(
        name="hospital",
        effects=[HealAllEffect(20)],
    ),
    "lazer": lambda: TurnCard(
        name="lazer",
        requires_target=True,
        targeted_effects=[("enemy", DamageEffect(30))],
    ),
    "ace": lambda: TurnCard(
        name="ace",
        effects=[DrawEffect(2)],
    ),
    "disk": lambda: TurnCard(
        name="disk",
        effects=[DrawTeamEffect(1)],
    ),
    "carder": lambda: TurnCard(
        name="carder",
        cost=[SelfDiscardCost(1)],
        effects=[DrawEffect(3)],
    ),
}