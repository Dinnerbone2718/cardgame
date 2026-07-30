import sys
import pygame
import screen
import map_state
import game as game_module
import player_state as player_state_module
import deck_screen as deck_screen_module
from global_value import Global
import random

pygame.init()


screen = screen.Screen(Global.SCREEN_WIDTH, Global.SCREEN_HEIGHT)


good = 0
bad = 0
average = 0

for _ in range(1):
    nodes, start_node, iterations = map_state.gen_map(screen, 50)

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


def start_combat(node):
    global mode, active_game
    config = map_state.get_fight_config(node)
    active_game = game_module.Game(screen, enemy_team_names=config.get("enemy_team"), player_state=player_state)
    mode = "combat"


def open_deck_screen():
    global mode
    deck_screen.open()
    mode = "deck"


def close_deck_screen():
    global mode
    mode = "map"


current_map = map_state.MapState(screen, nodes, start_node, on_combat_start=start_combat, on_deck_button_click=open_deck_screen)
deck_screen = deck_screen_module.DeckScreen(screen, player_state, on_close=close_deck_screen)

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

    if mode == "map":
        current_map.update(clock.get_time() / 1000)
        current_map.draw()
    elif mode == "combat":
        active_game.update(clock)
        active_game.draw()
    elif mode == "deck":
        deck_screen.draw()

    pygame.display.flip()

    clock.tick(FPS)

pygame.quit()
sys.exit()