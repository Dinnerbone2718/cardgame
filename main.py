import sys
import pygame
import screen
import map_state
import game as game_module
import player_state as player_state_module
import deck_screen as deck_screen_module
import shop_screen as shop_screen_module
import upgrade_screen as upgrade_screen_module
import card_screen as card_screen_module
from global_value import Global
import random

pygame.init()


screen = screen.Screen(Global.SCREEN_WIDTH, Global.SCREEN_HEIGHT)


good = 0
bad = 0
average = 0

for _ in range(1):
    nodes, start_node, iterations = map_state.gen_map(screen, 4)
    #nodes, start_node = map_state.build_example_map(screen)

    average+=iterations

    if iterations == 101:
        bad+=1
    else:
        good+=1


print("Success:")
print(good/(good+bad))

print("Average Attempts")
print(average/(good+bad))


mode = "map"
active_game = None

player_state = player_state_module.PlayerState()


WIN_COIN_BASE = 15
WIN_COIN_PER_DIFFICULTY = 15


def start_combat(node):
    global mode, active_game
    config = map_state.get_fight_config(node)
    difficulty = map_state.get_fight_difficulty(node)

    def handle_win():
        reward = WIN_COIN_BASE + difficulty * WIN_COIN_PER_DIFFICULTY
        player_state.add_coins(reward)
        end_combat()

    active_game = game_module.Game(
        screen,
        enemy_team_names=config.get("enemy_team"),
        player_state=player_state,
        on_win=handle_win,
        on_loss=end_combat,
    )
    mode = "combat"


def end_combat():
    global mode, active_game
    active_game = None
    mode = "map"


def open_deck_screen():
    global mode
    deck_screen.open()
    mode = "deck"


def close_deck_screen():
    global mode
    mode = "map"


def open_shop_screen(node):
    global mode
    shop_screen.open(node)
    mode = "shop"


def close_shop_screen():
    global mode
    mode = "map"


def open_upgrade_screen(node):
    global mode
    upgrade_screen.open(node)
    mode = "upgrade"


def close_upgrade_screen():
    global mode
    mode = "map"


def open_card_screen(node):
    global mode
    card_screen.open(node)
    mode = "card"


def close_card_screen():
    global mode
    mode = "map"


current_map = map_state.MapState(
    screen,
    nodes,
    start_node,
    player_state,
    on_combat_start=start_combat,
    on_deck_button_click=open_deck_screen,
    on_shop_enter=open_shop_screen,
    on_upgrade_enter=open_upgrade_screen,
    on_card_enter=open_card_screen,
)
deck_screen = deck_screen_module.DeckScreen(screen, player_state, on_close=close_deck_screen)
shop_screen = shop_screen_module.ShopScreen(screen, player_state, on_close=close_shop_screen)
upgrade_screen = upgrade_screen_module.UpgradeScreen(screen, player_state, on_close=close_upgrade_screen)
card_screen = card_screen_module.CardScreen(screen, player_state, on_close=close_card_screen)

clock = pygame.time.Clock()
FPS = 60

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen.resize(event.w, event.h)
        elif mode == "map":
            if event.type == pygame.MOUSEBUTTONDOWN:
                current_map.handle_mousedown(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                current_map.handle_mouseup(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                current_map.handle_mousemotion(event.pos)
        elif mode == "combat":
            if event.type == pygame.KEYDOWN:
                active_game.handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                active_game.handle_mousedown(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                active_game.handle_mouseup(event.pos)
        elif mode == "deck":
            if event.type == pygame.MOUSEBUTTONDOWN:
                deck_screen.handle_mousedown(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                deck_screen.handle_mouseup(event.pos)
        elif mode == "shop":
            if event.type == pygame.MOUSEBUTTONDOWN:
                shop_screen.handle_mousedown(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                shop_screen.handle_mouseup(event.pos)
        elif mode == "upgrade":
            if event.type == pygame.MOUSEBUTTONDOWN:
                upgrade_screen.handle_mousedown(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                upgrade_screen.handle_mouseup(event.pos)
        elif mode == "card":
            if event.type == pygame.MOUSEBUTTONDOWN:
                card_screen.handle_mousedown(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                card_screen.handle_mouseup(event.pos)

    if mode == "map":
        current_map.update(clock.get_time() / 1000)
        current_map.draw()
    elif mode == "combat":
        active_game.update(clock)
        if active_game is not None:
            active_game.draw()
    elif mode == "deck":
        deck_screen.draw()
    elif mode == "shop":
        shop_screen.draw()
    elif mode == "upgrade":
        upgrade_screen.update(clock.get_time() / 1000)
        upgrade_screen.draw()
    elif mode == "card":
        card_screen.draw()

    pygame.display.flip()

    clock.tick(FPS)

pygame.quit()
sys.exit()