import sys
import pygame
import screen
import map_state
import game as game_module
from global_value import Global
import random

pygame.init()


screen = screen.Screen(Global.SCREEN_WIDTH, Global.SCREEN_HEIGHT)


good = 0
bad = 0
average = 0

for _ in range(1):
    nodes, start_node, iterations = map_state.gen_map(screen, random.randint(0, 9999))

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


def start_combat(node):
    global mode, active_game
    config = map_state.get_fight_config(node)
    active_game = game_module.Game(screen, enemy_team_names=config.get("enemy_team"))
    mode = "combat"


current_map = map_state.MapState(screen, nodes, start_node, on_combat_start=start_combat)

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

    if mode == "map":
        current_map.update(clock.get_time() / 1000)
        current_map.draw()
    elif mode == "combat":
        active_game.update(clock)
        active_game.draw()

    pygame.display.flip()

    clock.tick(FPS)

pygame.quit()
sys.exit()