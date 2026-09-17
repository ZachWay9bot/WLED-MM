#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else '.') / 'usermods' / 'audioreactive' / 'audio_reactive.h'
s = p.read_text(encoding='utf-8')

marker = '''    // find the highest sample in the batch, and count zero crossings\n    float maxSample = 0.0f;                         // max sample from FFT batch\n'''

insert = '''    // 32EQ: gentle subsonic high-pass before level measurement and FFT.\n    // Removes DC, handling/room rumble and very-low-frequency microphone drift\n    // without throwing away the useful 30-80 Hz bass range.\n    // First-order HPF: fc = 25 Hz at the AudioReactive 22050 Hz sample rate.\n    // alpha = RC / (RC + dt) ~= 0.99293. State is preserved between FFT blocks.\n    constexpr float GEQ32_HPF_ALPHA = 0.99293f;\n    static float geq32HpfPrevIn = 0.0f;\n    static float geq32HpfPrevOut = 0.0f;\n    for (int i = 0; i < samplesFFT; i++) {\n      const float x = vReal[i];\n      const float y = GEQ32_HPF_ALPHA * (geq32HpfPrevOut + x - geq32HpfPrevIn);\n      geq32HpfPrevIn = x;\n      geq32HpfPrevOut = y;\n      vReal[i] = y;\n    }\n\n    // find the highest sample in the batch, and count zero crossings\n    float maxSample = 0.0f;                         // max sample from FFT batch\n'''

if marker not in s:
    raise SystemExit('HPF insertion point not found')
if 'GEQ32_HPF_ALPHA' in s:
    raise SystemExit('HPF already present')

s = s.replace(marker, insert, 1)
p.write_text(s, encoding='utf-8', newline='\n')
print('Applied 25 Hz subsonic HPF before level measurement and FFT')
