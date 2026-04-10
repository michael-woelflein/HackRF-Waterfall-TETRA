import time
import numpy as np

FB = "/dev/fb0"
W = 480
H = 320

WF_W = 400          # waterfall width
WF_H = 320
SIDEBAR_X = 400
SIDEBAR_W = 80

CHANNELS = 200
CH_W = 2            # 2 px per channel

assert CHANNELS * CH_W == WF_W

def rgb565(r, g, b):
    return np.uint16(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))

C_BLACK      = rgb565(0, 0, 0)
C_BG         = rgb565(0, 0, 8)
C_DARKBLUE   = rgb565(0, 8, 40)
C_BLUE       = rgb565(0, 40, 160)
C_GREEN      = rgb565(0, 220, 0)
C_YELLOW     = rgb565(255, 220, 0)
C_WHITE      = rgb565(255, 255, 255)
C_DARKGREY   = rgb565(40, 40, 40)
C_LIGHTGREY  = rgb565(160, 160, 160)
C_RED        = rgb565(255, 0, 0)

# 5x7 bitmap font for a few needed characters
FONT = {
    " ": ["00000","00000","00000","00000","00000","00000","00000"],
    ":": ["00000","00100","00100","00000","00100","00100","00000"],
    ".": ["00000","00000","00000","00000","00000","00100","00100"],
    "-": ["00000","00000","00000","01110","00000","00000","00000"],
    "0": ["01110","10001","10011","10101","11001","10001","01110"],
    "1": ["00100","01100","00100","00100","00100","00100","01110"],
    "2": ["01110","10001","00001","00010","00100","01000","11111"],
    "3": ["11110","00001","00001","01110","00001","00001","11110"],
    "4": ["00010","00110","01010","10010","11111","00010","00010"],
    "5": ["11111","10000","10000","11110","00001","00001","11110"],
    "6": ["01110","10000","10000","11110","10001","10001","01110"],
    "7": ["11111","00001","00010","00100","01000","01000","01000"],
    "8": ["01110","10001","10001","01110","10001","10001","01110"],
    "9": ["01110","10001","10001","01111","00001","00001","01110"],
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "C": ["01110","10001","10000","10000","10000","10001","01110"],
    "D": ["11110","10001","10001","10001","10001","10001","11110"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"],
    "F": ["11111","10000","10000","11110","10000","10000","10000"],
    "G": ["01110","10001","10000","10111","10001","10001","01110"],
    "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "I": ["01110","00100","00100","00100","00100","00100","01110"],
    "L": ["10000","10000","10000","10000","10000","10000","11111"],
    "M": ["10001","11011","10101","10101","10001","10001","10001"],
    "N": ["10001","11001","10101","10011","10001","10001","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "P": ["11110","10001","10001","11110","10000","10000","10000"],
    "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "S": ["01111","10000","10000","01110","00001","00001","11110"],
    "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "V": ["10001","10001","10001","10001","10001","01010","00100"],
    "Y": ["10001","10001","01010","00100","00100","00100","00100"],
}

def draw_rect(img, x, y, w, h, color):
    x2 = min(W, x + w)
    y2 = min(H, y + h)
    if x < x2 and y < y2:
        img[y:y2, x:x2] = color

def draw_char(img, x, y, ch, color, scale=1):
    glyph = FONT.get(ch.upper(), FONT[" "])
    for row, bits in enumerate(glyph):
        for col, bit in enumerate(bits):
            if bit == "1":
                draw_rect(img, x + col*scale, y + row*scale, scale, scale, color)

def draw_text(img, x, y, text, color, scale=1, spacing=1):
    cx = x
    for ch in text:
        draw_char(img, cx, y, ch, color, scale)
        cx += (5 * scale) + spacing

def write_frame(frame):
    with open(FB, "wb") as f:
        f.write(frame.astype(np.uint16).tobytes())

def power_to_color(v):
    # v is approximately 0..1
    if v < 0.20:
        return C_DARKBLUE
    elif v < 0.45:
        return C_BLUE
    elif v < 0.70:
        return C_GREEN
    elif v < 0.88:
        return C_YELLOW
    else:
        return C_WHITE

def make_sidebar(img, fps, threshold, decay):
    draw_rect(img, SIDEBAR_X, 0, SIDEBAR_W, H, C_BLACK)
    draw_rect(img, SIDEBAR_X, 0, 1, H, C_DARKGREY)

    draw_text(img, 408, 8,   "DEMO", C_WHITE, scale=2)
    draw_text(img, 408, 38,  "380", C_LIGHTGREY, scale=2)
    draw_text(img, 408, 58,  "-",   C_LIGHTGREY, scale=2)
    draw_text(img, 420, 58,  "385", C_LIGHTGREY, scale=2)
    draw_text(img, 408, 90,  "CH",  C_LIGHTGREY, scale=2)
    draw_text(img, 408, 110, "200", C_WHITE, scale=2)

    draw_text(img, 408, 150, "FPS", C_LIGHTGREY, scale=2)
    draw_text(img, 408, 170, f"{int(fps):02d}", C_WHITE, scale=2)

    draw_text(img, 408, 210, "THR", C_LIGHTGREY, scale=2)
    draw_text(img, 408, 230, f"{threshold:.1f}", C_WHITE, scale=2)

    draw_text(img, 408, 270, "DEC", C_LIGHTGREY, scale=2)
    draw_text(img, 408, 290, f"{decay:.2f}", C_WHITE, scale=2)

def generate_fake_channels(t, channels=CHANNELS):
    x = np.linspace(0, 1, channels, endpoint=False)

    noise = 0.08 + 0.07 * np.random.rand(channels)

    # moving signals
    sig1 = np.exp(-0.5 * ((x - ((0.15 + 0.08*np.sin(t*0.7)) % 1.0)) / 0.015)**2) * 0.85
    sig2 = np.exp(-0.5 * ((x - ((0.55 + 0.05*np.sin(t*1.3)) % 1.0)) / 0.025)**2) * 0.65
    sig3 = np.exp(-0.5 * ((x - ((0.82 + 0.03*np.cos(t*0.9)) % 1.0)) / 0.010)**2) * 1.00

    # bursty channels
    burst = np.zeros(channels)
    if int(t * 2) % 6 in (0, 1):
        burst[40:50] += 0.55
    if int(t * 3) % 10 in (3, 4, 5):
        burst[120:126] += 0.75

    vals = noise + sig1 + sig2 + sig3 + burst
    vals = np.clip(vals, 0.0, 1.0)
    return vals

def main():
    frame = np.full((H, W), C_BG, dtype=np.uint16)

    hold = np.zeros(CHANNELS, dtype=np.float32)
    threshold = 0.32
    decay = 0.035

    # initial sidebar
    make_sidebar(frame, 0, threshold, decay)
    write_frame(frame)

    last_time = time.time()
    fps = 0.0

    try:
        while True:
            now = time.time()
            dt = max(now - last_time, 1e-6)
            last_time = now
            fps = 0.9 * fps + 0.1 * (1.0 / dt)

            vals = generate_fake_channels(now)

            # persistence
            hold = np.maximum(vals, hold - decay)
            disp = np.maximum(vals, hold)

            # scroll waterfall up by 1 row
            frame[0:WF_H-1, 0:WF_W] = frame[1:WF_H, 0:WF_W]

            # build newest bottom row
            row = np.zeros(WF_W, dtype=np.uint16)
            for i in range(CHANNELS):
                c = power_to_color(float(disp[i]))
                x0 = i * CH_W
                row[x0:x0+CH_W] = c

            frame[WF_H-1, 0:WF_W] = row

            # redraw sidebar
            make_sidebar(frame, fps, threshold, decay)

            write_frame(frame)
            time.sleep(0.03)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
