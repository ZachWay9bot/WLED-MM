# DEXTER V11 NTP/DNS + STALL-WATCH freeze — 2026-11-21

This document records the frozen DEXTER long-run stability reference.

## Freeze identity

- Freeze branch: `freeze-dexter-v11-ntpfix-stallwatch-2026-11-21`
- Source fix commit: `771e51da8995c1e5a9c3e893879f723928ca3b1c`
- Freeze documentation commit: `4e7fbfefdc9d4fc8be95f14ffd7fdeaee3b2bdcb`
- Target: ESP32-WROOM-32, 4 MB flash
- PlatformIO environment: `esp32_4MB_V4_M`
- Build kit: `DEXTER_NTPFIX_STALLWATCH_ALL_IN_ONE_BUILDER_V11_2026-11-19.zip`
- Build kit SHA-256: `ae586406577a1a39ace5a438fb537a1f1184d96ac479de67f10addb7ea5cb4d3`

## Root cause and fix

The realtime UDP receiver remained healthy while the WLED main loop occasionally stopped servicing it for roughly 15 seconds. The independent stall watcher identified the blocking stage as `TIME/NTP`.

The ESP32 NTP path could synchronously call `WiFi.hostByName()` from the main loop. V11 moves NTP hostname resolution to a separate low-priority FreeRTOS task, caches the resolved server address, refreshes it in the background every six hours, and backs off failed lookups for 60 seconds.

V11 also fixes the cross-core stall-watch timestamp race and adds a largest-contiguous-heap preflight before large WebSocket allocations.

## Retained compatibility

- True 32-band local FFT and True32EQ effects.
- AudioSync V3 for real 32-band data.
- Unchanged AudioSync V2 stream for ESP8266 and other V2-only receivers.
- V2-to-32 interpolation fallback when V3 is absent.
- ARTIFX disabled in `esp32_4MB_V4_M`.
- Safe Error-33 handling without segment purge or forced WiFi reconnect solely due to low contiguous heap.
- Always-on AP recovery and direct realtime UDP diagnostics.

## Hardware validation before freeze

| Metric | Result |
| --- | ---: |
| Uptime | 8 h 41 min |
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

Do not rewrite this branch in place. Continue experiments on a separate development branch.
