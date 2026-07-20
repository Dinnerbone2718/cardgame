import pygame

ASPECT_RATIO = 16 / 9


class Screen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.surface = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)


        self.background_original = pygame.image.load("background/default.png").convert_alpha()
        self.background = pygame.transform.smoothscale(self.background_original, (self.width, self.height))

    def get_surface(self):
        return self.surface

    def resize(self, width, height):

        if height <= 0:
            height = 1
        if width / height > ASPECT_RATIO:
            width = round(height * ASPECT_RATIO)
        else:
            height = round(width / ASPECT_RATIO)

        self.width = width
        self.height = height
        self.surface = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.background = pygame.transform.smoothscale(self.background_original, (self.width, self.height))

    def draw(self):
        self.surface.blit(self.background, (0, 0))