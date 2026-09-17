# WLED-MM 14.7.1 – True 32-Band Audio EQ

Custom WLED-MM build based on **MoonModules/WLED-MM v14.7.1**, extended with a real 32-band audio spectrum path for ESP32.

The goal of this branch is a classic HiFi / Technics-style 32-column spectrum analyzer on a 32×8 addressable LED matrix while keeping the original WLED-MM 16-band audio path compatible with existing effects and AudioSync.

## Main changes

- Real **32-band FFT spectrum** derived from the raw 512-sample FFT bins.
- Original 16-band `fftResult` remains intact for stock WLED-MM effects.
- New 32-band data is exported through AudioReactive usermod data slot 12.
- Existing AudioSync protocol remains unchanged and compatible. AudioSync receivers without local FFT data fall back to interpolation from the legacy 16 bands.
- Gentle **25 Hz subsonic high-pass filter** before level measurement and FFT.
- ESP32-WROOM-32 / 4 MB build target: `esp32_4MB_V4_M`.

## 32-band frequency mapping

The 32-band path uses FFT-bin edges:

`1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 20, 23, 26, 30, 35, 40, 46, 53, 61, 70, 81, 93, 107, 123, 142, 163, 188, 216`

With the classic ESP32 AudioReactive sample rate of 22050 Hz and a 512-point FFT, this covers approximately **43 Hz to 9.3 kHz**. The low bands retain maximum resolution while the upper bands become progressively wider.

## Included 32-band effects

### GEQ 32 Classic

Classic fixed-column analyzer. Every X position represents one FFT band. On an 8-row matrix the level colors are fixed to:

- rows 1–3: green
- rows 4–6: yellow
- rows 7–8: red

Attack is immediate and release is controlled by the Fall Speed control. Peak Hold can be disabled completely by moving its control fully left.

### GEQ 32 Center

32 independent frequency columns growing symmetrically from the vertical center of the matrix.

### GEQ 32 Peaks

Minimal HiFi-style display showing the current frequency peaks as dots rather than full bars.

### GEQ 32 Waterfall

Frequency history display. Each new 32-band FFT frame enters as a new row and older spectrum data moves through the matrix.

### GEQ 32 Trace

A 32-point spectrum trace with fading persistence. Useful when a conventional bar graph is too visually busy.

## GEQ display behaviour

The analyzer deliberately uses a display envelope rather than horizontally smoothing neighboring frequency bands:

- fast / immediate attack
- controlled downward decay
- optional peak hold
- fixed frequency-to-column mapping
- no sideways 'snake' movement

For a 32×8 matrix this gives 32 frequency bands × 8 real vertical level steps.

## Microphone / AudioReactive notes

Development and testing has primarily targeted an **INMP441 I²S microphone**. The WLED-MM `INMP441 Big Speakers` audio profile can be a useful starting point for full-range systems with substantial low-frequency output.

AGC is not required for the 32-band effects. For a large speaker/subwoofer setup, running without AGC can give a more stable and natural spectrum because room and low-frequency background energy are not continuously amplified.

### Subsonic high-pass filter

This build adds a first-order **25 Hz HPF** to the local microphone samples before the Info level measurement and FFT. Its purpose is to suppress DC drift, handling noise and subsonic room/microphone rumble without using a hard 70–80 Hz cut. The useful 30–80 Hz bass region therefore remains available to the analyzer.

The filter state is continuous across FFT blocks. Both the legacy 16-band FFT and the local true 32-band FFT see the same filtered samples. The v2 gain behavior is otherwise unchanged.

## Building

A GitHub Actions workflow is included at:

`.github/workflows/build-32eq.yml`

It applies the 32-band, HiFi display, extra-effect and HPF patches and builds:

```text
pio run -e esp32_4MB_V4_M
```

The resulting firmware artifact is uploaded automatically by GitHub Actions as `WLEDMM_14.7.1_ESP32-WROOM32_32EQ-Classic-Plus-HPF`.

The source modifications are kept as patch scripts under `tools/` so the changes remain easy to inspect and re-apply against the exact WLED-MM 14.7.1 base.

## Base version

This branch is based on WLED-MM **v14.7.1**, commit:

`143c6d16204a807833fde0183d917ce84060ab62`

## Compatibility

This is an experimental custom build, not an official MoonModules release. Existing 16-band AudioReactive effects remain on the original data path. The new 32-band effects use local 32-band data when available.

Because the existing AudioSync packet contains 16 FFT bands, true 32-band spectrum data is currently local to the device performing the FFT. Extending AudioSync to transmit all 32 bands would require a protocol extension.

## License and upstream

This fork retains the original WLED / WLED-MM licensing and attribution. See `LICENSE` and the upstream project history for details.

Upstream project: MoonModules/WLED-MM
