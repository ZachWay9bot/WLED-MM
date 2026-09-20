# WLED-MM mdev True 32-Band EQ port

This branch ports the tested WLED-MM 14.7.1 true-32-band spectrum work onto the current `mdev` architecture without changing the 16-band AudioSync wire protocol.

## Architecture

- Base: WLED-MM `mdev`.
- AudioReactive is vendored under `lib/wled-audioreactive`, based on MoonModules/WLED-AudioReactive-Usermod commit `171c0bbc2bc47e2c11ae203dd00beed82865df2b`.
- The original 16-band `fftResult` remains unchanged for existing effects and AudioSync.
- A separate `fftResult32[32]` is exported as usermod data slot 12.
- Local ESP32 FFT produces true 32-band values directly from the 512-sample FFT data.
- AudioSync stays backward compatible at 16 bands. Received 16-band data is explicitly interpolated into slot 12.
- A 25 Hz first-order subsonic HPF is applied only to newly sampled data before it is stored in the 50% sliding FFT window, so overlapping samples are never filtered twice.

## 32-band bin edges

`1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 20, 23, 26, 30, 35, 40, 46, 53, 61, 70, 81, 93, 107, 123, 142, 163, 188, 216`

At 22050 Hz / 512 samples this covers roughly 43 Hz to 9.3 kHz.

## Effects

- GEQ 32 Classic
- GEQ 32 Center
- GEQ 32 Peaks
- GEQ 32 Waterfall
- GEQ 32 Trace

The mdev port uses effect IDs 230 through 233 and sets `MODE_COUNT` to 234.

## Automated validation

`tools/test_geq32_mapping.py` checks:

- edge count and monotonicity,
- expected frequency placement for representative test tones,
- legacy 16-to-32 AudioSync interpolation,
- the calculated 25 Hz HPF coefficient.

The branch workflow builds the actual port with `pio run -e esp32_4MB_V4_M` and uploads the resulting firmware.

## Hardware merge gate

Before merging into `mdev`, flash the workflow artifact to the target ESP32-WROOM-32 and verify:

1. Boot, Wi-Fi, Web UI and OTA.
2. INMP441 silence/noise floor and normal music.
3. Test tones at 50, 100, 250, 500, 1000, 2000, 5000 and 8000 Hz.
4. All five 32-band effects on the 32x8 matrix.
5. Existing 16-band AudioReactive effects.
6. AudioSync sender/receiver behavior. A receiver intentionally displays interpolated 32-band data because the wire protocol still carries 16 FFT bands.
7. Bass and level behavior with the 25 Hz HPF.

This is an experimental fork-only port until those hardware checks pass.
