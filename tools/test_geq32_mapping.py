#!/usr/bin/env python3
import math

SAMPLE_RATE=22050.0
FFT_SAMPLES=512
BIN_WIDTH=SAMPLE_RATE/FFT_SAMPLES
EDGES=[1,2,3,4,5,6,7,8,9,10,11,12,13,15,17,20,23,26,30,35,40,46,53,61,70,81,93,107,123,142,163,188,216]

assert len(EDGES)==33
assert all(a<b for a,b in zip(EDGES,EDGES[1:]))
assert EDGES[0]>=1 and EDGES[-1]<=FFT_SAMPLES//2

def band_for_frequency(freq):
    bin_index=max(1,min(int(round(freq/BIN_WIDTH)),FFT_SAMPLES//2-1))
    for i,(lo,hi) in enumerate(zip(EDGES,EDGES[1:])):
        if lo<=bin_index<hi:
            return i
    return 31

expected={
    50:(0,1),
    100:(1,2),
    250:(4,6),
    500:(10,12),
    1000:(15,17),
    2000:(20,22),
    5000:(27,29),
    8000:(30,31),
}
for freq,(lo,hi) in expected.items():
    band=band_for_frequency(freq)
    assert lo<=band<=hi,(freq,band,lo,hi)

legacy=[min(i*16,255) for i in range(16)]
out=[]
for i in range(32):
    a=i>>1
    b=min(a+1,15)
    out.append(((legacy[a]+legacy[b])>>1) if (i&1) else legacy[a])

assert out[0]==legacy[0]
assert out[1]==(legacy[0]+legacy[1])//2
assert out[2]==legacy[1]
assert out[31]==legacy[15]

alpha=1.0/(1.0+(2.0*math.pi*25.0/SAMPLE_RATE))
assert 0.9928<alpha<0.9931,alpha

print(f"GEQ32 checks OK; bin width={BIN_WIDTH:.5f} Hz, HPF alpha={alpha:.8f}")
