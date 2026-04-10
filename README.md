# HackRF-Waterfall-TETRA

sdr_waterfallv1.py is a real-time HackRF waterfall monitor for the 380-385 MHz band, drawing directly to the Linux framebuffer at /dev/fb0.

At a high level, it:

Starts hackrf_transfer to stream raw IQ samples centered at 382.5 MHz with a 10 MHz sample rate.
Splits that spectrum into 200 channels of 25 kHz each, which exactly covers 380-385 MHz.
Runs FFTs on incoming sample blocks, averages the power per 25 kHz channel, and estimates a moving noise floor.
Marks channels by how far above the noise floor they are, then color-codes them into a scrolling waterfall:
dark blue / blue = weak or near-noise
green / yellow / white = increasingly strong activity
Writes each new line into a 480x320 framebuffer display, with a 400 px waterfall and an 80 px sidebar.
The sidebar shows current settings and status, including LNA, VGA, AMP, threshold, decay, and FPS. The main loop in sdr_waterfallv1.py (line 305) also supports live keyboard control:

a / s: decrease / increase LNA

y / x: decrease / increase VGA

d: toggle amp

q / w: lower / raise detection threshold

e / r: lower / raise persistence decay

f / g: lower / raise target FPS

c: clear the waterfall and reset noise tracking

Esc: quit


# HackRF-Waterfall-TETRA
