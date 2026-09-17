#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else '.')/'wled00'/'FX.cpp'
s=p.read_text(encoding='utf-8')

old='const uint16_t fallPerSec=600 + ((uint32_t)SEGMENT.speed * 4200U / 255U);'
new='const uint16_t fallPerSec=1200 + ((uint32_t)SEGMENT.speed * 7200U / 255U);'
if old not in s: raise SystemExit('fall speed line not found')
s=s.replace(old,new,1)

old='const uint16_t peakHoldMs=70 + ((uint32_t)SEGMENT.intensity * 580U / 255U);'
new='const uint16_t peakHoldMs=(SEGMENT.intensity==0) ? 0 : (40 + ((uint32_t)SEGMENT.intensity * 1460U / 255U));'
if old not in s: raise SystemExit('peak hold line not found')
s=s.replace(old,new,1)

old_block='''    if(st->level[i]>=st->peak[i]) {\n      st->peak[i]=st->level[i];\n      st->peakHold[i]=peakHoldMs;\n    } else if(st->peakHold[i]>dt) {\n      st->peakHold[i]-=dt;\n    } else {\n      st->peakHold[i]=0;\n      st->peak[i]=(st->peak[i]>peakFallStep)?st->peak[i]-peakFallStep:0;\n      if(st->peak[i]<st->level[i]) st->peak[i]=st->level[i];\n    }\n'''
new_block='''    if(peakHoldMs==0) {\n      st->peak[i]=0;\n      st->peakHold[i]=0;\n    } else if(st->level[i]>st->peak[i]) {\n      // Only a genuinely new higher peak restarts the hold timer.\n      st->peak[i]=st->level[i];\n      st->peakHold[i]=peakHoldMs;\n    } else if(st->peakHold[i]>dt) {\n      st->peakHold[i]-=dt;\n    } else {\n      st->peakHold[i]=0;\n      st->peak[i]=(st->peak[i]>peakFallStep)?st->peak[i]-peakFallStep:0;\n      if(st->peak[i]<st->level[i]) st->peak[i]=st->level[i];\n    }\n'''
if old_block not in s: raise SystemExit('peak logic block not found')
s=s.replace(old_block,new_block,1)

p.write_text(s,encoding='utf-8',newline='\n')
print('HiFi controls retuned: peak-off at zero, true hold timing, faster fall range')
