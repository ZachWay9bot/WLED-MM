# WLED-MM mdev True 32-Band EQ

This fork carries the tested True 32-band spectrum implementation on the current WLED-MM `mdev` architecture while preserving the existing 16-band AudioSync wire protocol.

## Status

**Merged and hardware validated.** PR #2 was merged into `mdev` on 2026-09-25 after the dedicated True32EQ CI, the general WLED CI, and the ESP32-WROOM-32 hardware test all passed.

Merge commit: `6ad873305a85b1b9fc137c49725aa2ed0e554fe3`

The older WLED-MM 14.7.1 implementation remains available as the frozen reference and is not modified by this mdev port.

## Architecture

- Base: WLED-MM `mdev`.
- AudioReactive is vendored under `lib/wled-audioreactive`, based on MoonModules/WLED-AudioReactive-Usermod commit `171c0bbc2bc47e2c11ae203dd00beed82865df2b`.
- The original 16-band `fftResult` remains unchanged for existing effects and AudioSync.
- A separate `fftResult32[32]` is exported as usermod data slot 12.
- Local ESP32 FFT produces true 32-band values directly from the 512-sample FFT data.
- AudioSync stays backward compatible at 16 bands. Received 16-band data is explicitly interpolated into slot 12.
- A 25 Hz first-order subsonic HPF is applied only to newly sampled data before it is stored in the 50% sliding FFT window, so overlapping samples are never filtered twice.
- The firmware source is committed directly in C/C++. No Python source patcher is required for the firmware build. Python is retained only for validation/test infrastructure.

## 32-band bin edges

`1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 20, 23, 26, 30, 35, 40, 46, 53, 61, 70, 81, 93, 107, 123, 142, 163, 188, 216`

At 22050 Hz / 512 samples this covers roughly 43 Hz to 9.3 kHz.

## Effects

- GEQ 32 Classic
- GEQ 32 Center
- GEQ 32 Peaks
- GEQ 32 Waterfall
- GEQ 32 Trace

The additional effects use IDs 230 through 233 and `MODE_COUNT` is 234. GEQ 32 Classic uses the existing 2D GEQ slot with the True32EQ implementation.

## Compatibility

Existing 16-band AudioReactive effects remain compatible. AudioSync packets remain 16-band and therefore retain compatibility with the existing protocol. A receiving True32EQ node explicitly interpolates received 16-band FFT data to 32 display bands; locally sampled data uses the real 32-band FFT path.

## Validation

`tools/test_geq32_mapping.py` validates:

- edge count and monotonicity,
- expected frequency placement for representative test tones,
- legacy 16-to-32 AudioSync interpolation,
- the calculated 25 Hz HPF coefficient.

The dedicated workflow builds `esp32_4MB_V4_M` and uploads the ESP32-WROOM-32 firmware artifact.

Final merge gate completed on 2026-09-25:

1. Dedicated True32EQ mapping test and ESP32-WROOM-32 build: PASS.
2. General WLED CI: PASS.
3. ESP32-WROOM-32 hardware test: PASS.
4. Boot, Wi-Fi, Web UI and OTA: verified as part of the hardware gate.
5. INMP441/audio operation and True32EQ display operation: hardware validated.
6. Existing 16-band compatibility and AudioSync behavior: retained by design and covered by the merge gate.

## Upstream synchronization

The fork includes a guarded weekly MoonModules `mdev` synchronization workflow. Candidate upstream changes are merged, validated and built before either branch is pushed. A failed merge, validation, or build must not advance the maintained branches.
