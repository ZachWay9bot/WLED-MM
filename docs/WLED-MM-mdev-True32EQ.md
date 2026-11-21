# WLED-MM mdev True 32-Band EQ

This fork carries the tested True 32-band spectrum implementation on the current WLED-MM `mdev` architecture while preserving the existing 16-band AudioSync wire protocol.

## Status

**Merged and hardware validated.** PR #2 was merged into `mdev` on 2026-09-25 after the dedicated True32EQ CI, the general WLED CI, and the ESP32-WROOM-32 hardware test all passed.

Merge commit: `6ad873305a85b1b9fc137c49725aa2ed0e554fe3`

The older WLED-MM 14.7.1 implementation remains available as the frozen reference and is not modified by this mdev port.


### DEXTER V11 NTP/DNS stability freeze — 2026-11-21

The current DEXTER long-run stability reference is frozen on branch `freeze-dexter-v11-ntpfix-stallwatch-2026-11-21`.

The freeze fixes a measured ESP32 main-loop stall in the NTP path. The original implementation could call `WiFi.hostByName()` synchronously from `sendNTPPacket()`; field diagnostics captured recurring `TIME/NTP` stalls around 1.6 s and occasional UDP service gaps around 15 s. V11 moves DNS resolution to a low-priority FreeRTOS task, caches the resolved NTP address, refreshes it in the background every six hours, and backs off failed lookups for 60 seconds.

The same freeze retains the direct realtime UDP counters, main-loop stall watcher, ARTIFX RAM saving, always-on AP recovery, safe Error-33 behavior, and WebSocket contiguous-heap guard.

Hardware validation immediately before freeze:

- Uptime: **8 h 41 min**.
- Realtime UDP packets: **973,420**.
- Local UDP skips / mux misses / read errors: **0 / 0 / 0**.
- Maximum realtime UDP service gap: **131 ms**.
- Maximum realtime UDP packet processing time: **29 ms**.
- WiFi drops / soft reconnects / full reconnects: **0 / 0 / 0**.
- NTP DNS: **1 start / 1 success / 0 failures**, then cached address reuse.
- Stall watcher: **1 stall**, `CONNECTION`, **1.523 s**, occurring at startup; no later >500 ms stall was recorded during the validation window.
- Stall heap snapshot: **32.0 kB largest block / 49.9 kB free internal RAM**.

Source fix commit: `771e51da8995c1e5a9c3e893879f723928ca3b1c`.

The Windows reproducible build kit used for this freeze is `DEXTER_NTPFIX_STALLWATCH_ALL_IN_ONE_BUILDER_V11_2026-11-19.zip`, SHA-256 `ae586406577a1a39ace5a438fb537a1f1184d96ac479de67f10addb7ea5cb4d3`.

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

## Network True32EQ AudioSync

> [!IMPORTANT]
> **Hard compatibility rule: AudioSync V3 does not replace V2.**
>
> AudioSync V3 carries the real 32-band FFT data used by DEXTER/True32EQ ESP32 nodes. Legacy WLED/WLED-MM receivers, especially ESP8266 builds, only understand the normal V2 16-band packet. A sender that transmits V3 only would therefore leave those devices without usable AudioSync data.
>
> Required behavior:
>
> - **DEXTER/True32EQ ↔ DEXTER/True32EQ:** prefer V3 and use all 32 real FFT bands.
> - **Legacy/ESP8266 sender → DEXTER receiver:** receive V2 and locally interpolate the 16 received bands to 32 display values. These are display interpolation, not 32 independent FFT measurements.
> - **DEXTER sender → legacy/ESP8266 receiver:** the sender must keep a V2 stream available so the legacy receiver continues to work.
> - **Legacy ↔ legacy:** unchanged V2 operation.
>
> The current implementation sends the unchanged V2 packet plus an additive V3 packet on the same AudioSync transport. Because this doubles AudioSync packet traffic for a True32EQ sender, the transport is being reviewed as part of DEXTER long-run stability work. A future optimization may separate or negotiate V2/V3 traffic, but **removing the V2 legacy path is not an acceptable optimization**.
>
True32EQ nodes use an optional AudioSync V3 packet carrying all 32 FFT bands. The sender transmits the normal V2 16-band packet as well as the V3 32-band extension on the same AudioSync transport.

This makes fallback automatic:

- True32EQ sender + True32EQ receiver: receiver uses the real 32-band V3 data.
- True32EQ sender + stock/legacy receiver: receiver ignores V3 and continues using the normal 16-band V2 packet.
- Stock/legacy sender + True32EQ receiver: no V3 packet is present, so the receiver uses V2 and interpolates the 16 received bands to its 32 display bands.
- Stock/legacy sender + stock/legacy receiver: unchanged standard 16-band AudioSync.

The original V1/V2 packet layouts are not modified. The 32-band extension uses header `00003` and is additive, specifically to avoid breaking existing WLED/WLED-MM AudioSync nodes.

## Compatibility

Existing 16-band AudioReactive effects remain compatible. The legacy AudioSync V2 packet remains unchanged and is still transmitted for V2-only receivers; True32EQ adds a separate V3 packet carrying the real 32-band FFT data. A receiving True32EQ node uses V3 when available and otherwise explicitly interpolates received V2 16-band FFT data to 32 display bands; locally sampled data uses the real 32-band FFT path.

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
