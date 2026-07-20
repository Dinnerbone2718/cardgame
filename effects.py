class Effect:
    def apply(self, game, player, source, target):
        pass


class DamageEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        target.take_damage(self.amount)


class HealEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        target.heal(self.amount)


class DrawEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        for _ in range(self.amount):
            player.draw_card(game)


class HealTeamEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        team = game.player_team if player in game.player_team else game.enemy_team
        for unit in team:
            unit.heal(self.amount)


class DrawTeamEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        team = game.player_team if player in game.player_team else game.enemy_team
        for unit in team:
            for _ in range(self.amount):
                unit.draw_card(game)


class HealAllEffect(Effect):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, game, player, source, target):
        for unit in game.player_team + game.enemy_team:
            unit.heal(self.amount)


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
        unit.take_damage(self.amount)


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