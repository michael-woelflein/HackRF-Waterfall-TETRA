# SDR Waterfall Monitor

A lightweight real-time spectrum waterfall display for HackRF, focused on the 380-385 MHz band.

## What It Is For

This project is a simple on-device spectrum monitor for a Linux system with a framebuffer display and a connected HackRF.

The script captures IQ samples from the HackRF, analyzes the 380-385 MHz range in 25 kHz channels, estimates the current noise floor, and draws a scrolling color waterfall directly to `/dev/fb0`. The goal is to make it easy to see which parts of the band are active over time without needing a full desktop GUI or heavyweight SDR software.

This is useful for:

- Monitoring activity across the 380-385 MHz band
- Quickly spotting strong or persistent signals
- Running a compact SDR display on embedded or small-screen Linux hardware
- Experimenting with HackRF signal processing in Python

## Features

- Real-time waterfall display
- 200 channel view at 25 kHz per channel
- Noise-floor-relative signal highlighting
- Direct framebuffer output to `/dev/fb0`
- Live keyboard controls for gain, amplifier, threshold, decay, and frame rate
- Automatic HackRF restart if the sample stream drops

## Requirements

- Linux system with framebuffer access at `/dev/fb0`
- HackRF device
- `hackrf_transfer` installed and available in `PATH`
- Python 3
- `numpy`

## How It Works

The script:

1. Starts `hackrf_transfer` centered at 382.5 MHz with a 10 MHz sample rate
2. Covers the full 380-385 MHz band
3. Splits the band into 200 channels of 25 kHz each
4. Runs FFT processing on incoming IQ data
5. Estimates a moving noise floor
6. Colors each channel based on how far above the noise floor it is
7. Scrolls the display downward as new rows are added

Color intensity roughly indicates signal strength above the estimated noise floor:

- Dark blue: near background
- Blue: weak activity
- Green: active
- Yellow: strong
- White: very strong

## How To Run

Install Python dependencies:

```bash
pip install numpy
```

Make sure `hackrf_transfer` is installed and your HackRF is connected.

Run the script:

```bash
python3 sdr_waterfallv1.py
```

Depending on your system, access to `/dev/fb0` and the HackRF may require `sudo` or appropriate device permissions:

```bash
sudo python3 sdr_waterfallv1.py
```

## Keyboard Controls

While the program is running:

- `a`: decrease LNA gain
- `s`: increase LNA gain
- `y`: decrease VGA gain
- `x`: increase VGA gain
- `d`: toggle RF amplifier on or off
- `q`: lower detection threshold
- `w`: raise detection threshold
- `e`: lower persistence decay
- `r`: raise persistence decay
- `f`: lower target FPS
- `g`: raise target FPS
- `c`: clear the waterfall and reset the noise floor
- `Esc`: quit

## Default Tuning

Current script defaults:

- Band start: `380000000`
- Band stop: `385000000`
- Center frequency: `382500000`
- Sample rate: `10000000`
- FFT size: `2048`

These values are currently defined directly in [`sdr_waterfallv1.py`](/home/zer0data/SDR/sdr_waterfallv1.py).

## Notes

- This project writes directly to the framebuffer and does not use a desktop windowing system.
- The display is sized for a `480x320` screen layout.
- Sidebar values show current gain, amplifier state, threshold, decay, and frame rate.
- If the HackRF stream stops unexpectedly, the script attempts to restart it automatically.

## Future Improvements

- Command-line options for frequency range and gains
- Better install/setup instructions
- Optional desktop preview mode
- Signal logging or channel activity history
- Configurable color palettes and display sizes
