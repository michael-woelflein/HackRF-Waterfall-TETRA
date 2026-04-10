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

BAND_START = 380_000_000
BAND_STOP  = 385_000_000
CHANNEL_HZ = 25_000

CENTER_FREQ = 382_500_000
SAMPLE_RATE = 10_000_000
FFT_SIZE = 2048

LNA = 16
VGA = 16
AMP = False

LNA_MIN = 0
LNA_MAX = 24
LNA_STEP = 8

VGA_MIN = 0
VGA_MAX = 62
VGA_STEP = 2


# display / detection params
threshold_db = 6.0       # active when channel is this many dB above noise floor
persist_decay_db = 0.7   # dB/frame decay of persistence
target_fps = 15.0

def compute_row_bytes():
    raw = int((SAMPLE_RATE * 2) / target_fps)   # 2 bytes per complex sample
    block = FFT_SIZE * 2                        # bytes per FFT block
    raw = max(raw, block)
    raw = (raw // block) * block                # round down to whole FFT blocks
    return raw

ROW_BYTES = compute_row_bytes()

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
    "B": ["11110","10001","10001","11110","10001","10001","11110"],
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

def db_to_color(rel_db):
    # rel_db = channel dB above estimated noise floor
    if rel_db < 2.0:
        return C_DARKBLUE
    elif rel_db < threshold_db:
        return C_BLUE
    elif rel_db < threshold_db + 4.0:
        return C_GREEN
    elif rel_db < threshold_db + 10.0:
        return C_YELLOW
    return C_WHITE

def draw_sidebar(img, fps, noise_mean_db, peak_rel_db):
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

    draw_text(img, 408, 218, "THR", C_GREY, scale=1)
    draw_text(img, 408, 230, f"{threshold_db:4.1f}", C_WHITE, scale=1)

    draw_text(img, 408, 246, "DEC", C_GREY, scale=1)
    draw_text(img, 408, 258, f"{persist_decay_db:4.1f}", C_WHITE, scale=1)

    draw_text(img, 408, 274, "FPS", C_GREY, scale=1)
    draw_text(img, 408, 286, f"{fps:4.1f}", C_WHITE, scale=1)


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
    print("Starting:", " ".join(args), file=sys.stderr)
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
    time.sleep(0.08)
    return start_hackrf()

def read_proc_stderr(proc):
    if proc is None or proc.stderr is None:
        return ""
    try:
        data = proc.stderr.read()
        if not data:
            return ""
        return data.decode(errors="replace")
    except Exception:
        return ""


def read_exact(proc, nbytes):
    chunks = []
    total = 0

    while total < nbytes:
        chunk = proc.stdout.read(nbytes - total)
        if chunk is None or len(chunk) == 0:
            err = read_proc_stderr(proc)
            raise RuntimeError(
                f"short read from hackrf_transfer: got {total} bytes, expected {nbytes}\n{err}"
            )
        chunks.append(chunk)
        total += len(chunk)

    return b"".join(chunks)


def chunk_to_iq(raw):
    if len(raw) % 2 != 0:
        raw = raw[:-1]

    data = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
    return (data[0::2] + 1j * data[1::2]) / 128.0

def process_row_chunk(proc, window):
    raw = read_exact(proc, ROW_BYTES)
    iq = chunk_to_iq(raw)

    n_ffts = len(iq) // FFT_SIZE
    if n_ffts <= 0:
        raise RuntimeError("not enough IQ for one FFT")

    iq = iq[:n_ffts * FFT_SIZE]
    iq_blocks = iq.reshape(n_ffts, FFT_SIZE)

    # window and FFT all blocks at once
    fft = np.fft.fftshift(np.fft.fft(iq_blocks * window, axis=1), axes=1)
    power = (fft.real * fft.real) + (fft.imag * fft.imag)
    power_db = 10.0 * np.log10(power + 1e-12)

    # average channelized result across all FFTs in the row chunk
    accum = np.zeros(CHANNELS, dtype=np.float32)
    for i in range(n_ffts):
        accum += bin_channels_db(power_db[i])

    ch_db = accum / n_ffts
    return ch_db


def build_channel_map():
    freqs = np.fft.fftshift(np.fft.fftfreq(FFT_SIZE, d=1.0 / SAMPLE_RATE)) + CENTER_FREQ
    ch_index = np.floor((freqs - BAND_START) / CHANNEL_HZ).astype(np.int32)
    valid = (ch_index >= 0) & (ch_index < CHANNELS)
    valid_idx = np.nonzero(valid)[0]
    valid_ch = ch_index[valid]
    counts = np.bincount(valid_ch, minlength=CHANNELS).astype(np.float32)
    counts[counts == 0] = 1.0
    return valid_idx, valid_ch, counts

VALID_IDX, VALID_CH, CH_COUNTS = build_channel_map()

def bin_channels_db(power_db):
    # vectorized 25 kHz channelization
    sums = np.bincount(VALID_CH, weights=power_db[VALID_IDX], minlength=CHANNELS).astype(np.float32)
    ch_db = sums / CH_COUNTS
    return ch_db

def update_noise_floor(noise_db, ch_db):
    # asymmetric noise tracking:
    # - fast downward movement when band quiets down
    # - slow upward movement so active signals do not become the new floor too quickly
    if noise_db is None:
        return ch_db.copy()

    below = ch_db < (noise_db + 2.0)

    # fast attack downward / slow rise upward for quiet bins
    alpha_quiet = np.where(ch_db < noise_db, 0.18, 0.03)
    updated_quiet = (1.0 - alpha_quiet) * noise_db + alpha_quiet * ch_db

    # very slow update for bins currently above the floor
    updated_busy = 0.995 * noise_db + 0.005 * ch_db

    new_floor = np.where(below, updated_quiet, updated_busy)
    return new_floor

def get_key():
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if ready:
        return sys.stdin.read(1)
    return None



def main():
    global LNA, VGA, AMP, threshold_db, persist_decay_db, target_fps, ROW_BYTES

    frame = np.full((H, W), C_BG, dtype=np.uint16)
    hold_rel_db = np.zeros(CHANNELS, dtype=np.float32)
    noise_floor_db = None

    window = np.hanning(FFT_SIZE).astype(np.float32)

    proc = start_hackrf()

    old_term = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    fps_ema = 0.0
    last_frame_t = time.time()

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
                    threshold_db = max(0.0, threshold_db - 1.0)
                elif key == "w":
                    threshold_db = min(30.0, threshold_db + 1.0)
                elif key == "e":
                    persist_decay_db = max(0.1, persist_decay_db - 0.1)
                elif key == "r":
                    persist_decay_db = min(5.0, persist_decay_db + 0.1)
                elif key == "f":
                    target_fps = max(5.0, target_fps - 1.0)
                    ROW_BYTES = compute_row_bytes()
                elif key == "g":
                    target_fps = min(20.0, target_fps + 1.0)
                    ROW_BYTES = compute_row_bytes()
                elif key == "c":
                    hold_rel_db[:] = 0.0
                    frame[:, :WF_W] = C_BG
                    noise_floor_db = None
                elif key == "\x1b":
                    break

                if restart_needed:
                    try:
                        proc = restart_hackrf(proc)
                    except Exception:
                        LNA, VGA, AMP = old_lna, old_vga, old_amp
                        proc = restart_hackrf(proc)

            try:
                ch_db = process_row_chunk(proc, window)
            except RuntimeError as ex:
                print("\nHackRF stream died, restarting...", file=sys.stderr)
                print(ex, file=sys.stderr)
                proc = restart_hackrf(proc)
                time.sleep(0.2)
                continue

            noise_floor_db = update_noise_floor(noise_floor_db, ch_db)
            rel_db = ch_db - noise_floor_db
            rel_db = np.clip(rel_db, 0.0, 40.0)

            hold_rel_db = np.maximum(rel_db, hold_rel_db - persist_decay_db)
            disp_rel_db = np.maximum(rel_db, hold_rel_db)

            frame[:-1, :WF_W] = frame[1:, :WF_W]

            row = np.empty(WF_W, dtype=np.uint16)
            for i in range(CHANNELS):
                row[i * CH_W:(i + 1) * CH_W] = db_to_color(float(disp_rel_db[i]))

            frame[-1, :WF_W] = row

            now = time.time()
            dt = max(now - last_frame_t, 1e-6)
            last_frame_t = now
            fps_now = 1.0 / dt
            fps_ema = fps_now if fps_ema == 0.0 else (0.85 * fps_ema + 0.15 * fps_now)

            draw_sidebar(frame, fps_ema, float(np.mean(noise_floor_db)), float(np.max(rel_db)))
            write_frame(frame)

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term)
        stop_hackrf(proc)


if __name__ == "__main__":
    main()
