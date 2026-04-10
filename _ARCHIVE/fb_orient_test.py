import time
import numpy as np

FB = "/dev/fb0"
W = 480
H = 320

def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def make_pattern(w, h):
    img = np.zeros((h, w), dtype=np.uint16)

    # black background
    img[:, :] = rgb565(0, 0, 0)

    # colored borders
    img[0:12, :] = rgb565(255, 0, 0)        # top = red
    img[-12:, :] = rgb565(0, 255, 0)        # bottom = green
    img[:, 0:12] = rgb565(0, 0, 255)        # left = blue
    img[:, -12:] = rgb565(255, 255, 0)      # right = yellow

    # center box
    cy, cx = h // 2, w // 2
    img[cy-30:cy+30, cx-30:cx+30] = rgb565(255, 255, 255)

    return img

def write_frame(frame):
    with open(FB, "wb") as f:
        f.write(frame.astype(np.uint16).tobytes())

base = make_pattern(W, H)

tests = [
    ("base", base),
    ("rot90", np.rot90(base, 1)),
    ("rot180", np.rot90(base, 2)),
    ("rot270", np.rot90(base, 3)),
    ("flipud", np.flipud(base)),
    ("fliplr", np.fliplr(base)),
    ("transpose", base.T),
    ("transpose_flipud", np.flipud(base.T)),
    ("transpose_fliplr", np.fliplr(base.T)),
]

for name, frame in tests:
    # force back to 480x320 if transform changed shape
    if frame.shape != (H, W):
        fixed = np.zeros((H, W), dtype=np.uint16)
        hh = min(H, frame.shape[0])
        ww = min(W, frame.shape[1])
        fixed[:hh, :ww] = frame[:hh, :ww]
        frame = fixed

    print("showing:", name)
    write_frame(frame)
    time.sleep(2)
