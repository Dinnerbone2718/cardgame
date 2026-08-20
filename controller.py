import pygame
import math
import random
import statistics

class Controller:
    def __init__(self, game, player_controlled = False):
        self.game = game
        self.player_controlled = player_controlled

        self._selecter_image = pygame.image.load(f"assets/finger.png").convert_alpha()
        self._selecter_image_flipped = pygame.transform.flip(self._selecter_image, True, False)
        self._box_image = pygame.image.load(f"assets/box.png").convert_alpha()
        self._mouse_image = pygame.image.load(f"assets/mouse.png").convert_alpha()
        self._select_image = pygame.image.load(f"assets/select.png").convert_alpha()
        self._discard_image = pygame.image.load(f"assets/discard.png").convert_alpha()


        self.selecter_int = 0
        self.target_index = 0

        self.dragging = False
        self.drag_card = None
        self.drag_index = None
        self._last_card_rects = []

        self.pending_end_turn = False

        self.targeting = False
        self.pending_card = None
        self.pending_unit = None
        self.pending_specs = []
        self.pending_targets = []
        self.pending_stage = 0

        self.discarding = False
        self.pending_play_card = None
        self.pending_play_unit = None
        self.pending_discard_remaining = 0

        self.ai_actions = []
        self.ai_turn_started = False
        self.ai_phase = None
        self.ai_phase_elapsed = 0.0
        self.ai_wander_timer = 0.0
        self.ai_wander_target = None
        self.ai_select_final_unit = None
        self.ai_mouse_pos = None
        self.ai_card = None
        self.ai_card_index = None
        self.ai_move_from = None
        self.ai_move_to = None
        self.ai_pending_discards = []
        self.ai_current_discard = None
        self.ai_current_discard_index = None
        self.ai_post_discard_card = None
        self.ai_post_discard_unit = None


    def run_ai_turn(self):
        mode = 2

        if mode == 1:
            team = [unit for unit in self.get_team() if not unit.is_dead]
            if not team:
                return

            unit = random.choice(team)
            self.ai_select_unit(unit)

            if unit.hand:
                card = random.choice(unit.hand)
                self.ai_play_card(card)

        if mode == 2:
            print("New Turn: \n")
            team = [unit for unit in self.get_team() if not unit.is_dead]
            if not team:
                return
            best_score = None
            best_unit = None
            best_card = None

            for unit in team:
                for card in unit.hand:
                    score = self._score_outcome(card, unit)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_unit = unit
                        best_card = card

            if best_unit is not None and best_card is not None:
                self.ai_select_unit(best_unit)
                self.ai_play_card(best_card)




    def _get_average_health_perc(self):
        return statistics.mean([unit.health/unit.max_health for unit in self.get_team() if not unit.is_dead])

    def _get_opposing_health_perc(self):
        return statistics.mean([unit.health/unit.max_health for unit in self.get_opposing_team() if not unit.is_dead])

    def _get_cards_in_team(self):
        return sum([len(unit.hand) for unit in self.get_team()])

    def _get_cards_in_opp_team(self):
        return sum([len(unit.hand) for unit in self.get_opposing_team()])

    def _get_highest_hp_in_team(self):
        return max(self.get_team(), key=lambda x: x.health).health


    def _get_cards_in_hand(self, unit):
        return len(unit.hand)

    def _score_outcome(self, card, user):

        results = []

        own_alive = [u for u in self.get_team() if not u.is_dead]
        opp_alive = [u for u in self.get_opposing_team() if not u.is_dead]

        for effect in card.effects:
            effect_name = effect.__class__.__name__

            if effect_name == "HealAllEffect":
                results.append(("HealAllEffect", (self._get_opposing_health_perc() - self._get_average_health_perc()) * effect.amount))

            if effect_name == "HealTeamEffect":
                results.append(("HealTeamEffect", self._get_average_health_perc() * effect.amount))

            if effect_name == "HealEffect":
                results.append(("HealEffect", (1 - user.health / user.max_health) * effect.amount))

            if effect_name == "DamageEffect":
                results.append(("DamageEffect", -effect.amount))

            if effect_name == "DamageAllEffect":
                results.append(("DamageAllEffect", effect.amount * (len(opp_alive) - len(own_alive))))

            if effect_name == "DrawEffect":
                results.append(("DrawEffect", effect.amount * max(1, (5 - self._get_cards_in_hand(user)))))

            if effect_name == "DrawTeamEffect":
                results.append(("DrawTeamEffect", effect.amount * max(2, (15 - self._get_cards_in_team()))))


        for team, effect in card.targeted_effects:
            effect_name = effect.__class__.__name__
            sign = 1 if team == "enemy" else -1

            if effect_name == "DamageEffect":
                if effect.amount >= self._get_highest_hp_in_team() and sign == -1:
                    results.append((f"DamageEffect_{team}", -256))
                else:
                    results.append((f"DamageEffect_{team}", sign * effect.amount))


            if effect_name == "HealEffect":
                results.append((f"HealEffect_{team}", -sign * effect.amount))

            if effect_name == "DamageOrHealSelfEffect":
                attack_value = effect.damage_amount
                heal_value = (1 - user.health / user.max_health) * effect.heal_amount
                results.append((f"DamageOrHealSelfEffect_{team}", max(attack_value, heal_value)))

            if effect_name == "LifestealEffect":
                heal_value = (1 - user.health / user.max_health) * effect.amount * effect.heal_fraction
                results.append((f"LifestealEffect_{team}", effect.amount + heal_value))


        print(f"{user.name}, {card.name} : {sum(value for _, value in results)}")

        return sum(value for _, value in results)


    def draw(self):
        if self.player_controlled and self.game.turn != "player":
            return
        if not self.player_controlled and self.game.turn != "enemy":
            return

        size = self.game.screen.height // 5
        y = math.floor(self.selecter_int + 1) * (self.game.screen.height // 6)

        if self.player_controlled:
            image = self._selecter_image
            x = 0
        else:
            image = self._selecter_image_flipped
            x = self.game.screen.width - size

        self.game.screen.surface.blit(pygame.transform.smoothscale(image, (size, size)), (x, y))

        self.draw_hand()

        if self.player_controlled and self.targeting:
            self._draw_target_selection()

        if self.player_controlled and self.discarding:
            self._draw_discard_indicator()

        if not self.player_controlled and self.discarding_ai_active():
            self._draw_discard_indicator()

        if not self.player_controlled and self.ai_phase in ("select_unit", "approach", "drag", "discard_approach", "discard_drag") and self.ai_mouse_pos is not None:
            mouse_size = self.game.screen.height // 10
            cursor = pygame.transform.smoothscale(self._mouse_image, (mouse_size, mouse_size))
            rect = cursor.get_rect(center=(int(self.ai_mouse_pos[0]), int(self.ai_mouse_pos[1])))
            self.game.screen.surface.blit(cursor, rect)

    def _draw_animations_active(self):
        return any(unit.draw_animations for unit in self.game.player_team + self.game.enemy_team)

    def get_team(self):
        return self.game.player_team if self.player_controlled else self.game.enemy_team
    
    def get_opposing_team(self):
        return self.game.player_team if not self.player_controlled else self.game.enemy_team


    def get_opposing_team(self):
        return self.game.enemy_team if self.player_controlled else self.game.player_team

    def discarding_ai_active(self):
        return self.ai_phase in ("discard_approach", "discard_drag")

    def get_selected_unit(self):
        team = self.get_team()
        if not team:
            return None
        index = math.floor(self.selecter_int) % len(team)
        unit = team[index]
        if unit.is_dead:
            return None
        return unit

    def handle_keydown(self, key):
        if not self.player_controlled:
            return

        team = self.game.player_team
        if not team:
            return

        if key in (pygame.K_w, pygame.K_UP):
            self.move_selection(-1)
        elif key in (pygame.K_s, pygame.K_DOWN):
            self.move_selection(1)

    def move_selection(self, delta):
        team = self.get_team()
        if not team or all(unit.is_dead for unit in team):
            return
        index = self.target_index
        for _ in range(len(team)):
            index = (index + delta) % len(team)
            if team[index]:
                self.target_index = index
                return

    def get_card_size(self):
        width = self.game.screen.width
        card_width = max(1, width // 8)
        card_height = max(1, int(card_width * 1.4))
        return card_width, card_height

    def get_box_rect(self):
        card_width, card_height = self.get_card_size()
        box_width = int(card_width * (950 / 750))
        box_height = int(card_height * (1200 / 1000))
        width = self.game.screen.width
        height = self.game.screen.height
        rect = pygame.Rect(0, 0, box_width, box_height)
        rect.center = (width // 2, int(height * 0.42))
        return rect


            
            

    def draw_hand(self):
        unit = self.get_selected_unit()
        if unit is None or not unit.hand:
            return

        surface = self.game.screen.get_surface()
        width = self.game.screen.width
        height = self.game.screen.height

        hand = unit.hand
        count = len(hand)

        card_width, card_height = self.get_card_size()

        if self.dragging:
            box_rect = self.get_box_rect()
            box_image = pygame.transform.smoothscale(self._box_image, box_rect.size)
            surface.blit(box_image, box_rect)

        max_spread = min(60, 8 * (count - 1)) if count > 1 else 0
        angle_step = max_spread / (count - 1) if count > 1 else 0
        start_angle = max_spread / 2

        max_span = width * 0.7
        spacing = min(card_width * 0.55, max_span / max(count - 1, 1)) if count > 1 else 0

        center_x = width // 2
        base_y = height - card_height // 2 + card_height // 4

        if self.player_controlled and self.game.turn == "player":
            mouse_pos = pygame.mouse.get_pos()
        elif not self.player_controlled and self.ai_mouse_pos is not None:
            mouse_pos = (int(self.ai_mouse_pos[0]), int(self.ai_mouse_pos[1]))
        else:
            mouse_pos = (-10000, -10000)

        cards = []
        hovered_index = None
        self._last_card_rects = []
        for i, card in enumerate(hand):
            angle = start_angle - i * angle_step
            offset_x = (i - (count - 1) / 2) * spacing

            arc = abs(i - (count - 1) / 2)
            y_offset = (arc ** 2) * 3

            center = (center_x + offset_x, base_y + y_offset)
            rect = pygame.Rect(0, 0, card_width, card_height)
            rect.center = center

            cards.append({"card": card, "angle": angle, "center": center})
            self._last_card_rects.append((rect, i))

            if rect.collidepoint(mouse_pos) and not self.dragging:
                hovered_index = i

        animating = {id(a["card"]): a for a in unit.draw_animations}

        for i, data in enumerate(cards):
            if i == hovered_index or (self.dragging and i == self.drag_index):
                continue
            if id(data["card"]) in animating:
                continue
            image = pygame.transform.smoothscale(data["card"].get_image(), (card_width, card_height))
            rotated = pygame.transform.rotate(image, data["angle"])
            rect = rotated.get_rect(center=data["center"])
            surface.blit(rotated, rect)

        for i, data in enumerate(cards):
            anim = animating.get(id(data["card"]))
            if anim is None:
                continue
            t = max(0.0, min(1.0, anim["elapsed"] / anim["duration"]))
            eased = 1 - (1 - t) ** 3
            cx, cy = data["center"]
            start_y = -card_height
            y = start_y + (cy - start_y) * eased
            image = pygame.transform.smoothscale(data["card"].get_image(), (card_width, card_height))
            rotated = pygame.transform.rotate(image, data["angle"])
            rotated.set_alpha(int(255 * eased))
            rect = rotated.get_rect(center=(cx, y))
            surface.blit(rotated, rect)

        if hovered_index is not None:
            data = cards[hovered_index]
            hover_width = int(card_width * 1.25)
            hover_height = int(card_height * 1.25)
            cx, cy = data["center"]
            cy -= card_height * 0.35

            image = pygame.transform.smoothscale(data["card"].get_image(), (hover_width, hover_height))
            rotated = pygame.transform.rotate(image, data["angle"])
            rect = rotated.get_rect(center=(cx, cy))
            surface.blit(rotated, rect)

        if self.dragging and self.drag_card is not None:
            drag_width = int(card_width * 1.25)
            drag_height = int(card_height * 1.25)
            image = pygame.transform.smoothscale(self.drag_card.get_image(), (drag_width, drag_height))
            rect = image.get_rect(center=mouse_pos)
            surface.blit(image, rect)

    def get_drop_zone(self):
        return self.get_box_rect()

    def get_discard_box_rect(self):
        return self.get_box_rect()

    def _draw_discard_indicator(self):
        surface = self.game.screen.get_surface()
        card_width, _ = self.get_card_size()
        width = int(card_width * 1.6)
        height = width // 2
        image = pygame.transform.smoothscale(self._discard_image, (width, height))
        rect = image.get_rect(midtop=(self.game.screen.width // 2, int(self.game.screen.height * 0.03)))
        surface.blit(image, rect)

    def _draw_target_selection(self):
        valid = self._get_targets_for_current_stage()
        if not valid:
            return

        surface = self.game.screen.get_surface()
        for unit in valid:
            rect = self.game.get_unit_rect(unit)
            if rect is None:
                continue
            width = int(rect.width * 1.3)
            height = width // 2
            image = pygame.transform.smoothscale(self._select_image, (width, height))
            image_rect = image.get_rect(center=rect.center)
            surface.blit(image, image_rect)

    def _get_targets_for_current_stage(self):
        if not self.targeting or self.pending_stage >= len(self.pending_specs):
            return []
        team_type = self.pending_specs[self.pending_stage]

        if team_type == "enemy_or_self":
            targets = [unit for unit in self.get_opposing_team() if not unit.is_dead]
            caster = self.pending_unit
            if caster is not None and not caster.is_dead:
                targets.append(caster)
            return targets

        if team_type == "any":
            return [unit for unit in self.get_team() + self.get_opposing_team() if not unit.is_dead]

        team = self.get_opposing_team() if team_type == "enemy" else self.get_team()
        return [unit for unit in team if not unit.is_dead]

    def start_targeting(self, card, unit):
        self.targeting = True
        self.pending_card = card
        self.pending_unit = unit
        self.pending_specs = [team for team, _ in card.targeted_effects]
        self.pending_targets = []
        self.pending_stage = 0

    def _reset_targeting(self):
        self.targeting = False
        self.pending_card = None
        self.pending_unit = None
        self.pending_specs = []
        self.pending_targets = []
        self.pending_stage = 0

    def _handle_target_click(self, pos):
        target_unit = self.game.get_unit_at(pos)
        if target_unit is None:
            return

        valid = self._get_targets_for_current_stage()
        if target_unit not in valid:
            return

        self.pending_targets.append(target_unit)
        self.pending_stage += 1

        if self.pending_stage >= len(self.pending_specs):
            card = self.pending_card
            unit = self.pending_unit
            targets = self.pending_targets
            self._reset_targeting()
            card.play(self.game, unit, targets=targets)
            self.pending_end_turn = True

    def handle_mousedown(self, pos):
        if not self.player_controlled or self.game.turn != "player":
            return

        if self.targeting:
            self._handle_target_click(pos)
            return

        unit = self.get_selected_unit()
        if unit is None:
            return

        for rect, i in reversed(self._last_card_rects):
            if rect.collidepoint(pos):
                self.dragging = True
                self.drag_index = i
                self.drag_card = unit.hand[i]
                break

    def handle_mouseup(self, pos):
        if not self.dragging:
            return

        self.dragging = False
        card = self.drag_card
        index = self.drag_index
        self.drag_card = None
        self.drag_index = None

        if card is None:
            return

        if self.discarding:
            self._handle_discard_drop(card, index, pos)
            return

        if self.get_drop_zone().collidepoint(pos):
            self._play_card_now(card, index)

    def _handle_discard_drop(self, card, index, pos):
        if not self.get_discard_box_rect().collidepoint(pos):
            return

        unit = self.pending_play_unit
        if unit is not None and 0 <= index < len(unit.hand) and unit.hand[index] is card:
            unit.used_cards.append(unit.hand.pop(index))

        self.pending_discard_remaining -= 1

        if self.pending_discard_remaining <= 0:
            self._resolve_pending_play()

    def _resolve_pending_play(self):
        card = self.pending_play_card
        unit = self.pending_play_unit

        self.discarding = False
        self.pending_play_card = None
        self.pending_play_unit = None
        self.pending_discard_remaining = 0

        self._finish_playing_card(card, unit)

    def _play_card_now(self, card, index):
        unit = self.get_selected_unit()
        if unit is not None and 0 <= index < len(unit.hand) and unit.hand[index] is card:
            unit.used_cards.append(unit.hand.pop(index))

        interactive_costs = [c for c in card.cost if getattr(c, "interactive", False)]

        if interactive_costs:
            if self.player_controlled:
                self.pending_play_card = card
                self.pending_play_unit = unit
                self.pending_discard_remaining = sum(getattr(c, "amount", 1) for c in interactive_costs)
                self.discarding = True
                return
            else:
                self._begin_ai_post_play_discard(card, unit, interactive_costs)
                return

        self._finish_playing_card(card, unit)

    def _begin_ai_post_play_discard(self, card, unit, interactive_costs):
        discard_amount = sum(getattr(c, "amount", 1) for c in interactive_costs)
        others = list(unit.hand) if unit is not None else []
        self.ai_pending_discards = random.sample(others, min(discard_amount, len(others))) if others else []
        self.ai_post_discard_card = card
        self.ai_post_discard_unit = unit

        if self.ai_pending_discards:
            self._enter_ai_discard_step()
        else:
            self._finish_playing_card(card, unit)

    def _card_has_targets(self, card):
        for team_type, _ in card.targeted_effects:
            if team_type == "enemy_or_self":
                continue
            if team_type == "any":
                pool = self.get_team() + self.get_opposing_team()
            else:
                pool = self.get_opposing_team() if team_type == "enemy" else self.get_team()
            if not any(not unit.is_dead for unit in pool):
                return False
        return True

    def _finish_playing_card(self, card, unit):
        if unit is None or unit.is_dead:
            self.pending_end_turn = True
            return

        if card.requires_target:
            if not self._card_has_targets(card):
                self.pending_end_turn = True
                return

            if self.player_controlled:
                self.start_targeting(card, unit)
                return
            else:
                targets = []
                for team_type, effect in card.targeted_effects:
                    if team_type == "enemy_or_self":
                        pool = [u for u in self.get_opposing_team() if not u.is_dead]
                        if unit is not None and not unit.is_dead:
                            pool.append(unit)
                    elif team_type == "any":
                        pool = [u for u in (self.get_team() + self.get_opposing_team()) if not u.is_dead]
                    else:
                        pool = [u for u in (self.get_opposing_team() if team_type == "enemy" else self.get_team()) if not u.is_dead]
                        if not pool:
                            pool = [u for u in (self.get_team() if team_type == "enemy" else self.get_opposing_team()) if not u.is_dead]
                    targets.append(self._choose_ai_target(effect, team_type, pool, unit))
                card.play(self.game, unit, targets=targets)
        else:
            card.play(self.game, unit)

        self.pending_end_turn = True

    def _choose_ai_target(self, effect, team_type, pool, unit=None):

        effect_name = effect.__class__.__name__

        if effect_name == "DamageOrHealSelfEffect":
            enemies = [u for u in pool if u is not unit]
            if enemies:
                killable = [u for u in enemies if u.health <= effect.damage_amount]
                if killable:
                    return max(killable, key=lambda u: u.health)
                if unit is not None and unit.health < unit.max_health * 0.5:
                    return unit
                return min(enemies, key=lambda u: u.health)
            return unit

        if effect_name == "DamageEffect":
            if team_type == "enemy":
                killable = [u for u in pool if u.health <= effect.amount]
                if killable:
                    return max(killable, key=lambda u: u.health)
                return min(pool, key=lambda u: u.health)
            else:
                return max(pool, key=lambda u: u.health)

        if effect_name == "HealEffect":
            return min(pool, key=lambda u: u.health)

        if effect_name == "LifestealEffect":
            enemies = [u for u in pool if u in self.get_opposing_team()]
            if enemies:
                killable = [u for u in enemies if u.health <= effect.amount]
                if killable:
                    return max(killable, key=lambda u: u.health)
                return min(enemies, key=lambda u: u.health)
            return random.choice(pool)

        return random.choice(pool)

    def update(self, dt=None):
        if dt is None:
            dt = 1 / 60

        if self.pending_end_turn and not self._draw_animations_active():
            self.pending_end_turn = False
            self.game.end_turn()

        if not self.player_controlled:
            self.update_ai(dt)

        team = self.get_team()
        team_len = len(team) if team else 1

        diff = self.target_index - self.selecter_int
        if diff > team_len / 2:
            diff -= team_len
        elif diff < -team_len / 2:
            diff += team_len

        self.selecter_int = (self.selecter_int + diff * .25) % team_len

    def update_ai(self, dt):
        if self.game.turn != "enemy":
            self._reset_ai_state()
            return

        if self.ai_mouse_pos is None:
            self._init_ai_mouse_pos()

        if not self.ai_turn_started:
            self.ai_turn_started = True
            self.run_ai_turn()

        if self.ai_phase is None:
            self._start_next_ai_action()

        if self.ai_phase is None:
            if self._draw_animations_active():
                return
            self.game.end_turn()
            self._reset_ai_state()
            return

        self.ai_phase_elapsed += dt

        if self.ai_phase == "select_unit":
            self._update_ai_select_unit(dt)
        elif self.ai_phase == "discard_approach":
            self._update_ai_discard_approach()
        elif self.ai_phase == "discard_drag":
            self._update_ai_discard_drag()
        elif self.ai_phase == "approach":
            self._update_ai_approach()
        elif self.ai_phase == "drag":
            self._update_ai_drag()



    def ai_select_unit(self, unit):
        self.ai_actions.append(("select_unit", unit))

    def ai_play_card(self, card):
        self.ai_actions.append(("play_card", card))

    def _init_ai_mouse_pos(self):
        width = self.game.screen.width
        height = self.game.screen.height
        self.ai_mouse_pos = [width / 2, height * 0.9]

    def _start_next_ai_action(self):
        if not self.ai_actions:
            return

        kind, payload = self.ai_actions.pop(0)

        if kind == "select_unit":
            self._enter_ai_select_unit(payload)
        elif kind == "play_card":
            self._enter_ai_play_card(payload)

    def _enter_ai_select_unit(self, unit):
        team = self.get_team()
        if not team or unit not in team:
            return

        alive_indices = [i for i, u in enumerate(team) if not u.is_dead]
        if not alive_indices:
            return

        self.ai_phase = "select_unit"
        self.ai_phase_elapsed = 0.0
        self.ai_wander_timer = 0.0
        self.ai_wander_target = None
        self.ai_select_final_unit = unit
        self.target_index = random.choice(alive_indices)

    def _update_ai_select_unit(self, dt):
        width = self.game.screen.width
        height = self.game.screen.height
        team = self.get_team()

        self.ai_wander_timer -= dt
        if self.ai_wander_target is None or self.ai_wander_timer <= 0:
            self.ai_wander_timer = 0.7
            self.ai_wander_target = (random.uniform(width * 0.45, width * 0.55), random.uniform(height * 0.78, height * 0.88))
        self._drift_mouse_towards(self.ai_wander_target, dt, smoothing=3.0)

        if self.ai_phase_elapsed < 2.4:
            if math.floor(self.ai_phase_elapsed / 0.4) != math.floor((self.ai_phase_elapsed - dt) / 0.4):
                alive_indices = [i for i, u in enumerate(team) if not u.is_dead]
                if alive_indices:
                    self.target_index = random.choice(alive_indices)
        else:
            self.target_index = team.index(self.ai_select_final_unit)

        if self.ai_phase_elapsed >= 3.0:
            self.selecter_int = float(self.target_index)
            self.ai_phase = None

    def _enter_ai_play_card(self, card):
        unit = self.get_selected_unit()
        if unit is None or card not in unit.hand:
            return

        self.ai_card = card
        self.ai_card_index = unit.hand.index(card)
        self._enter_ai_card_approach()

    def _enter_ai_discard_step(self):
        unit = self.get_selected_unit()
        if not self.ai_pending_discards or unit is None:
            self._enter_ai_card_approach()
            return

        card = self.ai_pending_discards.pop(0)
        if card not in unit.hand:
            self._enter_ai_discard_step()
            return

        self.ai_current_discard = card
        self.ai_current_discard_index = unit.hand.index(card)

        self.ai_phase = "discard_approach"
        self.ai_phase_elapsed = 0.0
        self.ai_move_from = tuple(self.ai_mouse_pos)
        rect = self._get_card_rect(self.ai_current_discard_index)
        self.ai_move_to = rect.center if rect else self.ai_move_from

    def _update_ai_discard_approach(self):
        self._ease_mouse(0.6)
        if self.ai_phase_elapsed >= 0.6:
            self._enter_ai_discard_drag()

    def _enter_ai_discard_drag(self):
        self.ai_phase = "discard_drag"
        self.ai_phase_elapsed = 0.0
        self.ai_move_from = tuple(self.ai_mouse_pos)
        self.ai_move_to = self.get_box_rect().center
        self.dragging = True
        self.drag_card = self.ai_current_discard
        self.drag_index = self.ai_current_discard_index

    def _update_ai_discard_drag(self):
        self._ease_mouse(0.6)
        if self.ai_phase_elapsed >= 0.6:
            unit = self.get_selected_unit()
            card = self.ai_current_discard
            index = self.ai_current_discard_index

            self.dragging = False
            self.drag_card = None
            self.drag_index = None
            self.ai_current_discard = None
            self.ai_current_discard_index = None

            if unit is not None and card is not None and 0 <= index < len(unit.hand) and unit.hand[index] is card:
                unit.used_cards.append(unit.hand.pop(index))

            if self.ai_pending_discards:
                self._enter_ai_discard_step()
            else:
                self.ai_phase = None
                played_card = self.ai_post_discard_card
                played_unit = self.ai_post_discard_unit
                self.ai_post_discard_card = None
                self.ai_post_discard_unit = None
                if played_card is not None:
                    self._finish_playing_card(played_card, played_unit)

    def _enter_ai_card_approach(self):
        self.ai_phase = "approach"
        self.ai_phase_elapsed = 0.0
        self.ai_move_from = tuple(self.ai_mouse_pos)
        rect = self._get_card_rect(self.ai_card_index)
        self.ai_move_to = rect.center if rect else self.ai_move_from

    def _update_ai_approach(self):
        self._ease_mouse(0.6)
        if self.ai_phase_elapsed >= 0.6:
            self._enter_ai_drag()

    def _enter_ai_drag(self):
        self.ai_phase = "drag"
        self.ai_phase_elapsed = 0.0
        self.ai_move_from = tuple(self.ai_mouse_pos)
        self.ai_move_to = self.get_box_rect().center
        self.dragging = True
        self.drag_card = self.ai_card
        self.drag_index = self.ai_card_index

    def _update_ai_drag(self):
        self._ease_mouse(0.6)
        if self.ai_phase_elapsed >= 0.6:
            card = self.ai_card
            index = self.ai_card_index

            self.ai_phase = None
            self.ai_card = None
            self.ai_card_index = None
            self.dragging = False
            self.drag_card = None
            self.drag_index = None

            if card is not None:
                self._play_card_now(card, index)

    def _drift_mouse_towards(self, target, dt, smoothing=10.0):
        factor = 1 - math.exp(-smoothing * dt)
        tx, ty = target
        x, y = self.ai_mouse_pos
        self.ai_mouse_pos[0] = x + (tx - x) * factor
        self.ai_mouse_pos[1] = y + (ty - y) * factor

    def _ease_mouse(self, duration):
        t = min(1.0, self.ai_phase_elapsed / duration) if duration > 0 else 1.0
        eased = t * t * (3 - 2 * t)
        fx, fy = self.ai_move_from
        tx, ty = self.ai_move_to
        self.ai_mouse_pos[0] = fx + (tx - fx) * eased
        self.ai_mouse_pos[1] = fy + (ty - fy) * eased

    def _get_card_rect(self, index):
        for rect, i in self._last_card_rects:
            if i == index:
                return rect
        return None

    def _reset_ai_state(self):
        self.ai_actions = []
        self.ai_turn_started = False
        self.ai_phase = None
        self.ai_phase_elapsed = 0.0
        self.ai_mouse_pos = None
        self.ai_select_final_unit = None
        self.ai_card = None
        self.ai_card_index = None
        self.ai_pending_discards = []
        self.ai_current_discard = None
        self.ai_current_discard_index = None
        self.ai_post_discard_card = None
        self.ai_post_discard_unit = None
        self.dragging = False
        self.drag_card = None
        self.drag_index = None