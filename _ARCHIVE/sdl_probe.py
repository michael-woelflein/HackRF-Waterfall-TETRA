import os
import pygame

pygame.init()
print("pygame version:", pygame.version.ver)
print("SDL version:", pygame.get_sdl_version())

drivers = ["x11", "wayland", "KMSDRM", "kmsdrm", "fbcon", "directfb", "dummy", "offscreen"]
for drv in drivers:
    os.environ["SDL_VIDEODRIVER"] = drv
    try:
        pygame.display.quit()
        pygame.display.init()
        screen = pygame.display.set_mode((320, 240))
        print(f"OK: {drv}")
        pygame.display.quit()
    except Exception as e:
        print(f"NO: {drv} -> {e}")
