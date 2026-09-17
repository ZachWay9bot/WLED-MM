#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else '.')/'wled00'/'FX.cpp'
s=p.read_text(encoding='utf-8')
a=s.find('uint16_t mode_2DGEQ(void)')
b=s.find('static const char _data_FX_MODE_2DGEQ[]',a)
if a<0 or b<0: raise SystemExit('GEQ function not found')
f=r'''uint16_t mode_2DGEQ(void) {
  bool flatMode=!SEGMENT.is2D()||(SEGMENT.width()<3)||(SEGMENT.height()<3);
  const int NUM_BANDS=map2(SEGMENT.custom1,0,255,1,32);
  const int virtLength=SEGLEN;
  const uint16_t cols=flatMode?min(max(2,NUM_BANDS),(virtLength+1)/2):SEGMENT.virtualWidth();
  const uint16_t rows=flatMode?virtLength/cols:SEGMENT.virtualHeight();
  const unsigned offset=flatMode?max(0,(virtLength-rows*cols+1)/2):0;
  if(cols<=1||rows<=1) return mode_oops();

  struct GEQHiFiData {
    uint16_t level[32];       // 0..2040, 255 internal steps per LED
    uint16_t peak[32];
    uint16_t peakHold[32];
    uint32_t lastMs;
  };
  if(!SEGENV.allocateData(sizeof(GEQHiFiData))) return mode_oops();
  GEQHiFiData *st=reinterpret_cast<GEQHiFiData*>(SEGENV.data);

  if(SEGENV.call==0) {
    memset(st,0,sizeof(GEQHiFiData));
    st->lastMs=strip.now;
    SEGMENT.setUpLeds();
  }

  um_data_t *u=getAudioData();
  uint8_t v[32]={0};
  if(u->u_data&&u->u_size>12&&u->u_data[12]) memcpy(v,u->u_data[12],32);
  else if(u->u_data&&u->u_data[2]) {
    uint8_t *q=(uint8_t*)u->u_data[2];
    for(uint8_t i=0;i<32;i++){uint8_t x=i>>1,y=min((uint8_t)(x+1),(uint8_t)15);v[i]=(i&1)?(uint8_t)((q[x]+q[y])>>1):q[x];}
  }

  // INMP441 / large full-range speakers display calibration.
  // Stronger floor in the first bins suppresses room rumble; upper bands get a
  // mild lift so the 32-column display looks balanced rather than bass-heavy.
  static const uint8_t noiseFloor[32]={
    20,17,14,12,10,9,8,7,6,6,5,5,4,4,4,4,
     4, 4, 4, 4, 4,4,4,4,4,4,4,4,4,4,4,4
  };
  static const uint16_t gainQ8[32]={
    150,165,180,192,204,216,226,236,
    244,250,256,260,264,268,272,276,
    280,284,288,292,296,300,304,308,
    314,320,326,332,338,344,350,356
  };

  uint32_t now=strip.now;
  uint32_t dt=now-st->lastMs;
  if(dt<1) dt=1;
  if(dt>100) dt=100;
  st->lastMs=now;

  // speed: slow fall on the left, quicker fall on the right.
  // At the default middle position this is roughly 1 LED per 170 ms.
  const uint16_t fallPerSec=600 + ((uint32_t)SEGMENT.speed * 4200U / 255U);
  const uint16_t fallStep=max((uint16_t)1,(uint16_t)((uint32_t)fallPerSec*dt/1000U));
  // intensity controls peak hold: 70..650 ms.
  const uint16_t peakHoldMs=70 + ((uint32_t)SEGMENT.intensity * 580U / 255U);
  const uint16_t peakFallStep=max((uint16_t)1,(uint16_t)((uint32_t)fallStep/3U));

  for(uint8_t i=0;i<32;i++) {
    int raw=(int)v[i]-(int)noiseFloor[i];
    if(raw<0) raw=0;
    raw=(raw*(int)gainQ8[i])>>8;
    if(raw>255) raw=255;

    // Gentle quasi-log response: make musical detail readable without making
    // silence glow. Integer sqrt avoids floating-point cost in the effect loop.
    uint16_t shaped=0;
    if(raw>0) {
      uint32_t z=(uint32_t)raw*255U;
      uint32_t r=z;
      uint32_t prev=0;
      while(r!=prev){prev=r;r=(r+z/r)>>1;}
      shaped=(uint16_t)min((uint32_t)255,r);
    }
    uint16_t target=(uint32_t)shaped*(rows*255U)/255U;
    uint16_t maxLevel=rows*255U;
    if(target>maxLevel) target=maxLevel;

    // Technics-style envelope: immediate attack, deterministic slow release.
    if(target>=st->level[i]) st->level[i]=target;
    else st->level[i]=(st->level[i]>fallStep)?st->level[i]-fallStep:0;

    if(st->level[i]>=st->peak[i]) {
      st->peak[i]=st->level[i];
      st->peakHold[i]=peakHoldMs;
    } else if(st->peakHold[i]>dt) {
      st->peakHold[i]-=dt;
    } else {
      st->peakHold[i]=0;
      st->peak[i]=(st->peak[i]>peakFallStep)?st->peak[i]-peakFallStep:0;
      if(st->peak[i]<st->level[i]) st->peak[i]=st->level[i];
    }
  }

  SEGMENT.fill(BLACK);
  const uint8_t n=constrain(NUM_BANDS,1,32);
  for(uint16_t x=0;x<cols;x++){
    uint8_t band;
    if(cols==32&&n==32) band=x;
    else if(n==1) band=0;
    else {uint16_t lb=map(x,0,cols-1,0,n-1);band=(n<32)?map(lb,0,n-1,0,31):constrain((int)lb,0,31);}

    uint16_t h=(st->level[band]+254U)/255U;
    if(h>rows) h=rows;
    uint16_t hc=map(band,0,31,0,255);
    for(uint16_t y=0;y<h;y++){
      uint16_t ci=SEGMENT.check1?map(y,0,max(1,(int)rows-1),0,255):hc;
      uint32_t c=SEGMENT.color_from_palette(ci,false,PALETTE_SOLID_WRAP,0);
      setFlatPixelXY(flatMode,x,rows-1-y,c,cols,rows,offset);
    }

    // Peak marker. Keep it separate from the bar, like classic component GEQs.
    if(st->peak[band]>0) {
      uint16_t py=(st->peak[band]-1U)/255U;
      if(py>=rows) py=rows-1;
      uint16_t ci=SEGMENT.check1?map(py,0,max(1,(int)rows-1),0,255):hc;
      uint32_t pc=SEGMENT.color_from_palette(ci,false,PALETTE_SOLID_WRAP,0);
      setFlatPixelXY(flatMode,x,rows-1-py,pc,cols,rows,offset);
    }
  }
  return FRAMETIME;
}
'''
s=s[:a]+f+s[b:]
s=s.replace('static const char _data_FX_MODE_2DGEQ[] PROGMEM = "GEQ 32 ☾@Fade speed,Ripple decay,# of bands,,,Color bars,Smooth bars ☾;',
'''static const char _data_FX_MODE_2DGEQ[] PROGMEM = "GEQ 32 HiFi ☾@Fall speed,Peak hold,# of bands,,,Level colors,Unused ☾;''',1)
p.write_text(s,encoding='utf-8',newline='\n')
print('Technics-style 32-column HiFi GEQ enabled')
