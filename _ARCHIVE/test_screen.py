import os
import pygame
import time

# Force framebuffer output (important for SPI LCD)
os.environ["SDL_VIDEODRIVER"] = "fbcon"
os.environ["SDL_FBDEV"] = "/dev/fb0"
os.environ["SDL_NOMOUSE"] = "1"

pygame.init()

# Your LCD resolution
WIDTH = 480
HEIGHT = 320

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Test")

clock = pygame.time.Clock()

running = True
color = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # Animate color
    color = (color + 1) % 255
    screen.fill((color, 0, 255 - color))

    pygame.display.update()
    clock.tick(30)

pygame.quit()
