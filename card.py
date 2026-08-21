import pygame

from effects import (
    ApplyStatusTeamEffect,
    Cost,
    DamageByDiscardEffect,
    DamageEffect,
    DrawAllEffect,
    HealEffect,
    DrawEffect,
    HealTeamEffect,
    HealAllEffect,
    DrawTeamEffect,
    SelfDiscardCost,
    DamageAllEffect,
    Trigger,
    DamageOtherTeamEffect,
    DamageOrHealSelfEffect,
    LifestealEffect,
    ApplyStatusEffect,
    ApplyStatusOtherTeamEffect,
    Status,
)
from visual_effects import spawn_card_effect


CARD_NAMES = ["explosion", "field", "hospital", "lazer", "ace", "disk", "carder", "cuck", "dragon", "horse", "fartman", "donghuahorse", "cuck_friendship", "fox", "yogurt", "marmalade_peanut", "blorpit", "gronkle", "shield", "genius"]


def create_card(name):
    builder = _CARD_BUILDERS.get(name)
    if builder is None:
        return TurnCard(name=name, cost=None, requires_target=False, effects=None)
    return builder()


SHOP_BASE_PRICE = 20
SHOP_PRICE_PER_POWER = 10


class TurnCard:
    def __init__(self, name="default", cost=None, requires_target=False, effects=None, targeted_effects=None, power=3):
        self.name = name
        self.cost = cost if cost is not None else [Cost()]
        self.requires_target = requires_target
        self.effects = effects if effects is not None else []
        self.targeted_effects = targeted_effects if targeted_effects is not None else []
        self.power = power

    def get_shop_price(self):
        return SHOP_BASE_PRICE + self.power * SHOP_PRICE_PER_POWER

    def get_image(self):
        if not hasattr(self, "_image") or self._image is None:
            self._image = pygame.image.load(f"turn/{self.name}.png").convert_alpha()
        return self._image

    def can_play(self, game, player):
        return all(cost.can_pay(game, player) for cost in self.cost)

    def play(self, game, player, target=None, targets=None):
        if player is not None and player.is_dead:
            return

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
            if team == "enemy" and isinstance(effect, DamageEffect) and player is not None:
                player.trigger_passives(game, Trigger.ON_ATTACK, target=chosen_target)
            if team == "enemy_or_self" and isinstance(effect, DamageOrHealSelfEffect) and player is not None:
                if chosen_target is not player:
                    player.trigger_passives(game, Trigger.ON_ATTACK, target=chosen_target)
            if team == "any" and isinstance(effect, LifestealEffect) and player is not None:
                opposing_team = game.enemy_team if player in game.player_team else game.player_team
                if chosen_target in opposing_team:
                    player.trigger_passives(game, Trigger.ON_ATTACK, target=chosen_target)

        if player is not None:
            player.trigger_passives(game, Trigger.ON_PLAY)


_CARD_BUILDERS = {
    #Starter Cards
    "hospital": lambda: TurnCard(
        name="hospital",
        effects=[HealAllEffect(20)],
        power=1,
    ),
    "cuck": lambda: TurnCard(
        name="cuck",
        effects=[DamageAllEffect(10)],
        power=1,
    ),
    "lazer": lambda: TurnCard(
        name="lazer",
        requires_target=True,
        targeted_effects=[("enemy", DamageEffect(30))],
        power=2,
    ),
    "ace": lambda: TurnCard(
        name="ace",
        effects=[DrawEffect(2)],
        power=2,
    ),
    "dragon": lambda: TurnCard(
        name="dragon",
        effects=[DrawEffect(1), HealEffect(10)],
        power=2,
    ),

    #Early Game Upgrades
    "field": lambda: TurnCard(
        name="field",
        effects=[HealEffect(40)],
        power=3,
    ),
    "disk": lambda: TurnCard(
        name="disk",
        effects=[DrawTeamEffect(1)],
        power=3,
    ),
    "carder": lambda: TurnCard(
        name="carder",
        cost=[SelfDiscardCost(1)],
        effects=[DrawEffect(3)],
        power=3,
    ),

    "fox": lambda: TurnCard(
        name="fox",
        requires_target=True,
        targeted_effects=[("any", LifestealEffect(20))],
        power=3,
    ),

    "marmalade_peanut": lambda: TurnCard(
        name="marmalade_peanut",
        requires_target=False,
        effects=[DamageAllEffect(10)],
        power=3,
    ),


    "yogurt": lambda: TurnCard(
        name="yogurt",
        effects=[DrawAllEffect(2)],
        power=3,
    ),


    "genius": lambda: TurnCard(
        name="genius",
        requires_target=True,
        targeted_effects=[("enemy", DamageByDiscardEffect(10))],
        power=4,
    ),

    #Later Game Upgrades
    "explosion": lambda: TurnCard(
        name="explosion",
        requires_target=True,
        targeted_effects=[("enemy", DamageEffect(50)), ("ally", DamageEffect(20))],
        power=4,
    ),
    "horse": lambda: TurnCard(
        name="horse",
        requires_target=True,
        effects=[HealEffect(999)],
        targeted_effects=[("ally", DamageEffect(999))],
        power=4,
    ),
    "fartman": lambda: TurnCard(
        name="fartman",
        requires_target=True,
        targeted_effects=[("enemy", DamageEffect(40))],
        power=4,
    ),

    "cuck_friendship": lambda: TurnCard(
        name="cuck_friendship",
        requires_target=True,
        targeted_effects=[("enemy_or_self", DamageOrHealSelfEffect(20, heal_amount=20))],
        power=3,
    ),

    "donghuahorse": lambda: TurnCard(
        name="donghuahorse",
        requires_target=False,
        effects=[DamageOtherTeamEffect(10)],
        power=5,),

    #Status Cards
    "blorpit": lambda: TurnCard(
        name="blorpit",
        requires_target=True,
        targeted_effects=[("enemy", ApplyStatusEffect(Status.POISON, 4))],
        power=2,
    ),

    "gronkle": lambda: TurnCard(
        name="gronkle",
        requires_target=False,
        effects=[ApplyStatusOtherTeamEffect(Status.WEAKEN, 2)],
        power=3,
    ),

    "shield": lambda: TurnCard(
        name="shield",
        requires_target=False,
        effects=[ApplyStatusEffect(Status.SHIELD, 2)],
        power=3,
    )

}

HIGH_TIER_CARDS = [name for name in CARD_NAMES if create_card(name).power >= 4]