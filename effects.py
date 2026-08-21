from enum import Enum


class Trigger(Enum):
    ON_PLAY = "on_play"
    ON_ATTACK = "on_attack"
    ON_DEATH = "on_death"
    ON_TURN_START = "on_turn_start"


class Status:
    POISON = "poison"
    WEAKEN = "weaken"
    SHIELD = "shield"


class Effect:
    def apply(self, game, player, source, target):
        pass


class DamageEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        amount = self.amount
        if source is not None and getattr(source, "glass_cannon", False):
            amount *= 2
        target.take_damage(amount, game, source)


class DamageAllEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        amount = self.amount
        if source is not None and getattr(source, "glass_cannon", False):
            amount *= 2
        for unit in game.player_team + game.enemy_team:
            unit.take_damage(amount, game, source)

class HealEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        target.heal(self.amount)


class DamageOrHealSelfEffect(Effect):
    def __init__(self, damage_amount, heal_amount=None):
        self.damage_amount = damage_amount
        self.heal_amount = heal_amount if heal_amount is not None else damage_amount

    def apply(self, game, player, source, target):
        if target is source:
            target.heal(self.heal_amount)
            return

        amount = self.damage_amount
        if source is not None and getattr(source, "glass_cannon", False):
            amount *= 2
        target.take_damage(amount, game, source)


class LifestealEffect(Effect):

    def __init__(self, amount, heal_fraction=0.5):
        self.amount = amount
        self.heal_fraction = heal_fraction

    def apply(self, game, player, source, target):
        amount = self.amount
        if source is not None and getattr(source, "glass_cannon", False):
            amount *= 2
        target.take_damage(amount, game, source)
        if source is not None and not source.is_dead:
            source.heal(int(amount * self.heal_fraction))


class DrawEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        total = self.amount + getattr(player, "extra_draw_count", 0)
        for _ in range(total):
            player.draw_card(game)


class HealTeamEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        team = game.player_team if player in game.player_team else game.enemy_team
        for unit in team:
            unit.heal(self.amount)


class DamageOtherTeamEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        amount = self.amount
        if source is not None and getattr(source, "glass_cannon", False):
            amount *= 2
        team = game.player_team if not player in game.player_team else game.enemy_team
        for unit in team:
            unit.take_damage(amount, game, source)

class DrawTeamEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        team = game.player_team if player in game.player_team else game.enemy_team
        for unit in team:
            total = self.amount + getattr(unit, "extra_draw_count", 0)
            for _ in range(total):
                unit.draw_card(game)


class DrawAllEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        for unit in game.player_team + game.enemy_team:
            total = self.amount + getattr(unit, "extra_draw_count", 0)
            for _ in range(total):
                unit.draw_card(game)


class HealAllEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        for unit in game.player_team + game.enemy_team:
            unit.heal(self.amount)


class ApplyStatusEffect(Effect):

    def __init__(self, status_name, amount):
        self.status_name = status_name
        self.amount = amount

    def apply(self, game, player, source, target):
        if target is not None:
            target.add_status(self.status_name, self.amount)


class ApplyStatusOtherTeamEffect(Effect):

    def __init__(self, status_name, amount):
        self.status_name = status_name
        self.amount = amount

    def apply(self, game, player, source, target):
        team = game.player_team if player not in game.player_team else game.enemy_team
        for unit in team:
            if not unit.is_dead:
                unit.add_status(self.status_name, self.amount)


class ApplyStatusTeamEffect(Effect):

    def __init__(self, status_name, amount):
        self.status_name = status_name
        self.amount = amount

    def apply(self, game, player, source, target):
        team = game.player_team if player in game.player_team else game.enemy_team
        for unit in team:
            if not unit.is_dead:
                unit.add_status(self.status_name, self.amount)


class Cost:
    interactive = False

    def can_pay(self, game, player):
        return True

    def pay(self, game, player):
        pass


class DiscardCost(Cost):
    def __init__(self, amount):
        self.amount = amount

    def can_pay(self, game, player):
        return len(player.hand) >= self.amount

    def pay(self, game, player):
        for _ in range(self.amount):
            player.select_discard_card()


class HealthCost(Cost):
    def __init__(self, amount):
        self.amount = amount

    def can_pay(self, game, player):
        return any(unit.health > self.amount for unit in player.units)

    def pay(self, game, player):
        unit = player.select_damage_target()
        unit.take_damage(self.amount, game, player)


class SelfDiscardCost(Cost):

    interactive = True

    def __init__(self, amount):
        self.amount = amount

    def can_pay(self, game, player):
        return len(player.hand) >= self.amount

    def pay(self, game, player):
        for _ in range(self.amount):
            if player.hand:
                player.hand.pop(0)





class DamageByDiscardEffect(DamageEffect):

    def __init__(self, amount_per_card):
        super().__init__(amount_per_card)
        self.amount_per_card = amount_per_card

    def apply(self, game, player, source, target):
        discard_count = len(getattr(source, "used_cards", None) or [])
        amount = self.amount_per_card * discard_count
        if source is not None and getattr(source, "glass_cannon", False):
            amount *= 2
        target.take_damage(amount, game, source)