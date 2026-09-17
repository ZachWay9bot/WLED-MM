#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else '.')/'wled00'/'FX.cpp'
s=p.read_text(encoding='utf-8')
old='''    int raw=(int)v[i]-(int)noiseFloor[i];\n    if(raw<0) raw=0;\n    raw=(raw*(int)gainQ8[i])>>8;\n    if(raw>255) raw=255;\n'''
new='''    int raw=(int)v[i];\n    // Big-Speakers preset already handles mic/noise conditioning.\n    // Do not subtract another floor here or quiet bands vanish completely.\n    static const uint16_t visualGainQ8[32]={\n      236,238,240,242,244,246,248,250,252,254,256,258,260,262,264,266,\n      268,270,272,274,276,278,280,282,284,286,288,290,292,294,296,298\n    };\n    raw=(raw*(int)visualGainQ8[i])>>8;\n    if(raw>255) raw=255;\n    if(raw<2) raw=0;\n'''
if old not in s: raise SystemExit('target gain block not found')
s=s.replace(old,new,1)
old_sqrt='''    // Gentle quasi-log response: make musical detail readable without making\n    // silence glow. Integer sqrt avoids floating-point cost in the effect loop.\n    uint16_t shaped=0;\n    if(raw>0) {\n      uint32_t z=(uint32_t)raw*255U;\n      uint32_t r=z;\n      uint32_t prev=0;\n      while(r!=prev){prev=r;r=(r+z/r)>>1;}\n      shaped=(uint16_t)min((uint32_t)255,r);\n    }\n'''
new_sqrt='''    // Safe quasi-log display shaping. The previous integer Newton loop could\n    // oscillate forever between two adjacent values and watchdog-reset the ESP.\n    uint16_t shaped=0;\n    if(raw>0) {\n      float norm=(float)raw/255.0f;\n      shaped=(uint16_t)constrain((int)(sqrtf(norm)*255.0f+0.5f),0,255);\n    }\n'''
if old_sqrt not in s: raise SystemExit('target sqrt block not found')
s=s.replace(old_sqrt,new_sqrt,1)
p.write_text(s,encoding='utf-8',newline='\n')
print('HiFi GEQ double-gating removed and sqrt loop fixed')
