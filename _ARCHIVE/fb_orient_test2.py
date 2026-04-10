import time
import numpy as np

FB = "/dev/fb0"
W = 480
H = 320

def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

C_BLACK  = rgb565(0, 0, 0)
C_WHITE  = rgb565(255, 255, 255)
C_RED    = rgb565(255, 0, 0)
C_GREEN  = rgb565(0, 255, 0)
C_BLUE   = rgb565(0, 0, 255)
C_YELLOW = rgb565(255, 255, 0)
C_CYAN   = rgb565(0, 255, 255)
C_MAG    = rgb565(255, 0, 255)

def make_pattern(w, h):
    img = np.full((h, w), C_BLACK, dtype=np.uint16)

    # Uneven border sizes so flips/rotations are obvious
    img[0:10, :] = C_RED          # top
    img[-20:, :] = C_GREEN        # bottom
    img[:, 0:30] = C_BLUE         # left
    img[:, -40:] = C_YELLOW       # right

    # Different corner boxes
    img[20:60, 40:100] = C_WHITE          # near top-left
    img[30:90, w-140:w-60] = C_CYAN       # near top-right
    img[h-100:h-40, 60:140] = C_MAG       # near bottom-left

    # One skinny vertical bar off-center
    img[80:260, 220:228] = C_WHITE

    # One horizontal bar near bottom
    img[250:258, 180:360] = C_CYAN

    return img

def force_shape(frame, h=H, w=W):
    out = np.full((h, w), C_BLACK, dtype=np.uint16)
    hh = min(h, frame.shape[0])
    ww = min(w, frame.shape[1])
    out[:hh, :ww] = frame[:hh, :ww]
    return out

def write_frame(frame):
    with open(FB, "wb") as f:
        f.write(frame.astype(np.uint16).tobytes())

base = make_pattern(W, H)

tests = [
    ("base", base),
    ("rot180", np.rot90(base, 2)),
    ("flipud", np.flipud(base)),
    ("fliplr", np.fliplr(base)),
]

for name, frame in tests:
    frame = force_shape(frame)
    print("showing:", name)
    write_frame(frame)
    time.sleep(3)
