import sys
import pygame
import screen
import game

pygame.init()

SCREEN_WIDTH = 960*1.2
SCREEN_HEIGHT = 540*1.2
screen = screen.Screen(SCREEN_WIDTH, SCREEN_HEIGHT)
game = game.Game(screen)

clock = pygame.time.Clock()
FPS = 60

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen.resize(event.w, event.h)
        elif event.type == pygame.KEYDOWN:
            game.handle_keydown(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            game.handle_mousedown(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            game.handle_mouseup(event.pos)


    game.update(clock)
    game.draw()

    pygame.display.flip()  

    clock.tick(FPS)

pygame.quit()
sys.exit()