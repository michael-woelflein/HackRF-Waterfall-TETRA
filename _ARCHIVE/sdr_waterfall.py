import subprocess
import numpy as np
import time
import sys
import termios
import tty
import select

FB = "/dev/fb0"
W = 480
H = 320
WF_W = 400
SIDEBAR_X = 400
SIDEBAR_W = 80

CHANNELS = 200
CH_W = 2

CENTER_FREQ = 382500000
SAMPLE_RATE = 10000000
FFT_SIZE = 1024

LNA = 16
VGA = 16
AMP = False

LNA_MIN = 0
LNA_MAX = 24
LNA_STEP = 8

VGA_MIN = 0
VGA_MAX = 62
VGA_STEP = 2


threshold = 0.30
decay = 0.02

def rgb565(r, g, b):
    return np.uint16(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))

C_BG        = rgb565(0, 0, 8)
C_BLACK     = rgb565(0, 0, 0)
C_DARKBLUE  = rgb565(0, 8, 40)
C_BLUE      = rgb565(0, 40, 160)
C_GREEN     = rgb565(0, 220, 0)
C_YELLOW    = rgb565(255, 220, 0)
C_WHITE     = rgb565(255, 255, 255)
C_GREY      = rgb565(90, 90, 90)

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
    "U": ["10001","10001","10001","10001","10001","10001","01110"],
    "V": ["10001","10001","10001","10001","10001","01010","00100"],
    "W": ["10001","10001","10001","10101","10101","10101","01010"],
    "X": ["10001","10001","01010","00100","01010","10001","10001"],
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
                draw_rect(img, x + col * scale, y + row * scale, scale, scale, color)

def draw_text(img, x, y, text, color, scale=1, spacing=1):
    cx = x
    for ch in text:
        draw_char(img, cx, y, ch, color, scale)
        cx += (5 * scale) + spacing

def write_frame(frame):
    with open(FB, "wb") as f:
        f.write(frame.astype(np.uint16).tobytes())

def power_to_color(v):
    if v < threshold:
        return C_DARKBLUE
    elif v < threshold + 0.15:
        return C_BLUE
    elif v < threshold + 0.35:
        return C_GREEN
    elif v < threshold + 0.55:
        return C_YELLOW
    return C_WHITE

def draw_sidebar(img):
    draw_rect(img, SIDEBAR_X, 0, SIDEBAR_W, H, C_BLACK)
    draw_rect(img, SIDEBAR_X, 0, 1, H, C_GREY)

    draw_text(img, 408, 8,   "MON", C_WHITE, scale=2)
    draw_text(img, 408, 36,  "380", C_WHITE, scale=2)
    draw_text(img, 408, 56,  "-",   C_WHITE, scale=2)
    draw_text(img, 420, 56,  "385", C_WHITE, scale=2)

    draw_text(img, 408, 90,  "LNA", C_GREY, scale=1)
    draw_text(img, 408, 102, f"{LNA:02d}", C_WHITE, scale=2)

    draw_text(img, 408, 132, "VGA", C_GREY, scale=1)
    draw_text(img, 408, 144, f"{VGA:02d}", C_WHITE, scale=2)

    draw_text(img, 408, 174, "AMP", C_GREY, scale=1)
    draw_text(img, 408, 186, "ON" if AMP else "OFF", C_WHITE, scale=2)

    draw_text(img, 408, 220, "THR", C_GREY, scale=1)
    draw_text(img, 408, 232, f"{threshold:.2f}", C_WHITE, scale=1)

    draw_text(img, 408, 262, "DEC", C_GREY, scale=1)
    draw_text(img, 408, 274, f"{decay:.3f}", C_WHITE, scale=1)

def start_hackrf():
    args = [
        "hackrf_transfer",
        "-r", "-",
        "-f", str(CENTER_FREQ),
        "-s", str(SAMPLE_RATE),
        "-l", str(LNA),
        "-g", str(VGA),
        "-a", "1" if AMP else "0",
    ]
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0
    )

def stop_hackrf(proc):
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=0.5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

def restart_hackrf(proc):
    stop_hackrf(proc)
    time.sleep(0.1)
    return start_hackrf()

def read_samples(proc, n):
    need = n * 2
    raw = proc.stdout.read(need)
    if raw is None or len(raw) < need:
        raise RuntimeError(f"short read from hackrf_transfer: got {0 if raw is None else len(raw)} bytes, expected {need}")
    data = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
    iq = (data[0::2] + 1j * data[1::2]) / 128.0
    return iq

def process_fft(iq):
    window = np.hanning(len(iq))
    iq = iq * window
    fft = np.fft.fftshift(np.fft.fft(iq))
    power = 10 * np.log10(np.abs(fft) ** 2 + 1e-12)
    return power


def bin_channels(power):
    freqs = np.linspace(
        CENTER_FREQ - SAMPLE_RATE/2,
        CENTER_FREQ + SAMPLE_RATE/2,
        len(power),
        endpoint=False
    )

    channel_power = np.zeros(CHANNELS)
    counts = np.zeros(CHANNELS)

    for i in range(len(power)):
        f = freqs[i]

        # only keep 380–385 MHz
        if f < 380e6 or f >= 385e6:
            continue

        ch = int((f - 380e6) / 25000)  # 25 kHz bins

        if 0 <= ch < CHANNELS:
            channel_power[ch] += power[i]
            counts[ch] += 1

    # average
    for i in range(CHANNELS):
        if counts[i] > 0:
            channel_power[i] /= counts[i]

    # normalize
    channel_power -= np.min(channel_power)
    peak = np.max(channel_power)
    if peak > 0:
        channel_power /= peak

    return channel_power



def get_key():
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if ready:
        return sys.stdin.read(1)
    return None



def main():
    global LNA, VGA, AMP, threshold, decay

    frame = np.full((H, W), C_BG, dtype=np.uint16)
    hold = np.zeros(CHANNELS, dtype=np.float32)

    proc = start_hackrf()

    old = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            key = get_key()
            restart_needed = False

            old_lna, old_vga, old_amp = LNA, VGA, AMP

            if key:
                if key == "y":
                    VGA = max(VGA_MIN, VGA - VGA_STEP)
                    restart_needed = True
                elif key == "x":
                    VGA = min(VGA_MAX, VGA + VGA_STEP)
                    restart_needed = True
                elif key == "a":
                    LNA = max(LNA_MIN, LNA - LNA_STEP)
                    restart_needed = True
                elif key == "s":
                    LNA = min(LNA_MAX, LNA + LNA_STEP)
                    restart_needed = True
                elif key == "d":
                    AMP = not AMP
                    restart_needed = True
                elif key == "q":
                    threshold = max(0.0, threshold - 0.02)
                elif key == "w":
                    threshold = min(1.0, threshold + 0.02)
                elif key == "e":
                    decay = max(0.001, decay - 0.005)
                elif key == "r":
                    decay = min(0.2, decay + 0.005)
                elif key == "c":
                    hold[:] = 0.0
                    frame[:, :WF_W] = C_BG
                elif key == "\x1b":
                    break

                if restart_needed:
                    try:
                        proc = restart_hackrf(proc)
                    except Exception:
                        LNA, VGA, AMP = old_lna, old_vga, old_amp
                        proc = restart_hackrf(proc)

            iq = read_samples(proc, FFT_SIZE)
            power = process_fft(iq)
            bins = bin_channels(power)

            hold = np.maximum(bins, hold - decay)
            disp = np.maximum(bins, hold)

            frame[:-1, :WF_W] = frame[1:, :WF_W]

            row = np.empty(WF_W, dtype=np.uint16)
            for i in range(CHANNELS):
                row[i * CH_W:(i + 1) * CH_W] = power_to_color(float(disp[i]))

            frame[-1, :WF_W] = row
            draw_sidebar(frame)

            write_frame(frame)

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        stop_hackrf(proc)





if __name__ == "__main__":
    main()
