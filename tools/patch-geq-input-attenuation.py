#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else '.')/'usermods'/'audioreactive'/'audio_reactive.h'
s=p.read_text(encoding='utf-8')
marker='''    // find the highest sample in the batch, and count zero crossings\n    float maxSample = 0.0f;                         // max sample from FFT batch\n'''
insert='''    // 32EQ HiFi v3: attenuate sensitive INMP441 input before both Info level and FFT.\n    // This is a true front-end attenuation, not merely a display scaling.\n    constexpr float INMP441_INPUT_ATTENUATION = 0.30f;\n    for (int i=0; i < samplesFFT; i++) vReal[i] *= INMP441_INPUT_ATTENUATION;\n\n    // find the highest sample in the batch, and count zero crossings\n    float maxSample = 0.0f;                         // max sample from FFT batch\n'''
if marker not in s: raise SystemExit('sample attenuation insertion point not found')
s=s.replace(marker,insert,1)
# Reduce the intentional minimum gain pedestal in both the original 16-band path
# and our 32-band path. Keep a small non-zero pedestal so Gain=0 still gives a
# faint usable analyzer response instead of hard-zeroing FFT output.
s=s.replace('+ 1.0f/16.0f)', '+ 1.0f/64.0f)')
s=s.replace('+ 1.0f / 16.0f)', '+ 1.0f / 64.0f)')
p.write_text(s,encoding='utf-8',newline='\n')
print('INMP441 front-end attenuation 0.30 and reduced minimum gain pedestal applied')
