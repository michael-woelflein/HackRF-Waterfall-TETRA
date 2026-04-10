import os
import time
import numpy as np

FB = "/dev/fb0"
WIDTH = 320
HEIGHT = 480

def rgb888_to_rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def make_solid(width, height, r, g, b):
    color = rgb888_to_rgb565(r, g, b)
    frame = np.full((height, width), color, dtype=np.uint16)
    return frame

def make_gradient(width, height, phase):
    x = np.arange(width, dtype=np.uint16)
    y = np.arange(height, dtype=np.uint16)[:, None]

    r = ((x + phase) % 256).astype(np.uint8)
    g = ((y + phase) % 256).astype(np.uint8)
    b = (((x // 2 + y // 2 + phase) % 256)).astype(np.uint8)

    # Expand to full image shape
    rr = np.tile(r, (height, 1))
    gg = np.tile(g, (1, width))
    bb = b

    frame = (
        ((rr.astype(np.uint16) & 0xF8) << 8) |
        ((gg.astype(np.uint16) & 0xFC) << 3) |
        (bb.astype(np.uint16) >> 3)
    ).astype(np.uint16)

    return frame

def write_frame(frame):
    # rotate 90 degrees
   # frame = np.rot90(frame, k=3)
    frame = np.flipud(frame)
    with open(FB, "wb") as f:
        f.write(frame.tobytes())

# Quick color cycle first
write_frame(make_solid(WIDTH, HEIGHT, 255, 0, 0))
time.sleep(1)
write_frame(make_solid(WIDTH, HEIGHT, 0, 255, 0))
time.sleep(1)
write_frame(make_solid(WIDTH, HEIGHT, 0, 0, 255))
time.sleep(1)

# Animated gradient
for phase in range(0, 256, 4):
    frame = make_gradient(WIDTH, HEIGHT, phase)
    write_frame(frame)
    time.sleep(0.03)
