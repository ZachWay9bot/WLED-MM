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

  um_data_t *u=getAudioData();
  uint8_t v[32]={0};
  if(u->u_data&&u->u_size>12&&u->u_data[12]) memcpy(v,u->u_data[12],32);
  else if(u->u_data&&u->u_data[2]) {
    uint8_t *q=(uint8_t*)u->u_data[2];
    for(uint8_t i=0;i<32;i++){uint8_t x=i>>1,y=min((uint8_t)(x+1),(uint8_t)15);v[i]=(i&1)?(uint8_t)((q[x]+q[y])>>1):q[x];}
  }

  if(SEGENV.call==0) SEGMENT.setUpLeds();
  SEGMENT.fill(BLACK);
  const uint8_t n=constrain(NUM_BANDS,1,32);
  for(uint16_t x=0;x<cols;x++){
    uint8_t band;
    if(cols==32&&n==32) band=x;
    else if(n==1) band=0;
    else {uint16_t lb=map(x,0,cols-1,0,n-1);band=(n<32)?map(lb,0,n-1,0,31):constrain((int)lb,0,31);}
    uint16_t h=map2(v[band],0,255,0,rows); if(h>rows) h=rows;
    uint16_t hc=map(band,0,31,0,255);
    for(uint16_t y=0;y<h;y++){
      uint16_t ci=SEGMENT.check1?map(y,0,max(1,(int)rows-1),0,255):hc;
      uint32_t c=SEGMENT.color_from_palette(ci,false,PALETTE_SOLID_WRAP,0);
      setFlatPixelXY(flatMode,x,rows-1-y,c,cols,rows,offset);
    }
  }
  return FRAMETIME;
}
'''
s=s[:a]+f+s[b:]
s=s.replace('static const char _data_FX_MODE_2DGEQ[] PROGMEM = "GEQ 32 ☾@Fade speed,Ripple decay,# of bands,,,Color bars,Smooth bars ☾;','static const char _data_FX_MODE_2DGEQ[] PROGMEM = "GEQ 32 Direct ☾@Unused,Unused,# of bands,,,Color bars,Unused ☾;',1)
p.write_text(s,encoding='utf-8',newline='\n')
print('direct 32-column GEQ enabled')
