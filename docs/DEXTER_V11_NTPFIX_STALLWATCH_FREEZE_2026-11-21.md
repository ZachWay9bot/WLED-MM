# DEXTER V11 NTP/DNS + STALL-WATCH freeze — 2026-11-21

This document records the frozen DEXTER long-run stability reference.

## Freeze identity

- Freeze branch: `freeze-dexter-v11-ntpfix-stallwatch-2026-11-21`
- Source fix commit: `771e51da8995c1e5a9c3e893879f723928ca3b1c`
- Target: ESP32-WROOM-32, 4 MB flash
- PlatformIO environment: `esp32_4MB_V4_M`
- Build kit: `DEXTER_NTPFIX_STALLWATCH_ALL_IN_ONE_BUILDER_V11_2026-11-19.zip`
- Build kit SHA-256: `ae586406577a1a39ace5a438fb537a1f1184d96ac479de67f10addb7ea5cb4d3`

## Why V11 exists

Long-run diagnostics showed that the realtime UDP receiver itself remained healthy while the WLED main loop occasionally stopped servicing it for roughly 15 seconds. The independent stall watcher then identified the blocking stage as `TIME/NTP`.

The ESP32 NTP send path could synchronously resolve `ntpServerName` through `WiFi.hostByName()` from the main loop. That lookup produced measured stalls around 1.6 seconds and, when DNS was slow, service gaps around 15 seconds.

V11 changes the ESP32 path so that:

- NTP hostname resolution runs in a separate low-priority FreeRTOS task.
- The Arduino main loop does not wait on `hostByName()`.
- A successful NTP server address is cached.
- The cache is refreshed in the background every six hours.
- Failed DNS resolution backs off for 60 seconds.
- DNS starts, successes, failures, busy state and cached IP are exposed in the Info page.
- The cross-core stall watcher timestamp race is guarded so unsigned underflow no longer produces `4294967295 ms` fake stalls.
- Large WebSocket allocations are preflighted against the largest contiguous heap block to reduce allocation thrashing when fragmentation is severe.

## Retained DEXTER behavior

- True 32-band local FFT and True32EQ effects.
- AudioSync V3 for real 32-band data.
- Unchanged AudioSync V2 legacy stream for ESP8266 and other V2-only nodes.
- V2-to-32 local interpolation fallback on a DEXTER receiver when V3 is absent.
- ARTIFX disabled in `esp32_4MB_V4_M` to save internal RAM.
- Safe Error-33 handling: no segment purge and no forced WiFi reconnect solely because of low contiguous heap.
- Always-on AP recovery.
- Direct realtime UDP and main-loop stall diagnostics.

## Hardware validation before freeze

The tested receiver reported after **8 h 41 min**:

| Metric | Result |
| --- | ---: |
| Realtime UDP packets | 973,420 |
| Local UDP skips | 0 |
| UDP mux misses | 0 |
| UDP read errors | 0 |
| Max UDP service gap | 131 ms |
| Max UDP process time | 29 ms |
| WiFi drops | 0 |
| Soft reconnects | 0 |
| Full reconnects | 0 |
| NTP DNS | 1 start / 1 success / 0 failures |
| Stall count >500 ms | 1 |
| Last/max stall | CONNECTION, 1.523 s |
| Stall heap snapshot | 32.0 kB largest / 49.9 kB free internal |

The single recorded stall occurred at startup. No later >500 ms stall was recorded during the validation window.

## Freeze rule

This branch is a reference point. Further experiments should be developed on another branch; do not rewrite this freeze in place.
