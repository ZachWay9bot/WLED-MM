#!/usr/bin/env python3
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
fxp=root/'wled00'/'FX.cpp'
hp=root/'wled00'/'FX.h'
fx=fxp.read_text(encoding='utf-8')
h=hp.read_text(encoding='utf-8')

def once(s,old,new,name):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{name}: expected 1 match, got {n}')
    return s.replace(old,new,1)

# ---------------------------------------------------------------------------
# Effect IDs. 228..231 are free directly after the v14.7.1 MODE_COUNT=228.
# ---------------------------------------------------------------------------
old='''#define FX_MODE_PS1DSPRINGY            227\n\n#define MODE_COUNT                     228\n'''
new='''#define FX_MODE_PS1DSPRINGY            227\n\n// Custom WLED-MM 14.7.1 true-32-band audio effects\n#define FX_MODE_GEQ32CENTER             228\n#define FX_MODE_GEQ32PEAKS              229\n#define FX_MODE_GEQ32WATERFALL          230\n#define FX_MODE_GEQ32TRACE              231\n\n#define MODE_COUNT                     232\n'''
h=once(h,old,new,'effect IDs')

# ---------------------------------------------------------------------------
# Turn the existing v2 HiFi analyzer into fixed Technics-style row colors.
# y here is height measured from the bottom of the bar.
# ---------------------------------------------------------------------------
old='''    uint16_t h=(st->level[band]+254U)/255U;\n    if(h>rows) h=rows;\n    uint16_t hc=map(band,0,31,0,255);\n    for(uint16_t y=0;y<h;y++){\n      uint16_t ci=SEGMENT.check1?map(y,0,max(1,(int)rows-1),0,255):hc;\n      uint32_t c=SEGMENT.color_from_palette(ci,false,PALETTE_SOLID_WRAP,0);\n      setFlatPixelXY(flatMode,x,rows-1-y,c,cols,rows,offset);\n    }\n\n    // Peak marker. Keep it separate from the bar, like classic component GEQs.\n    if(st->peak[band]>0) {\n      uint16_t py=(st->peak[band]-1U)/255U;\n      if(py>=rows) py=rows-1;\n      uint16_t ci=SEGMENT.check1?map(py,0,max(1,(int)rows-1),0,255):hc;\n      uint32_t pc=SEGMENT.color_from_palette(ci,false,PALETTE_SOLID_WRAP,0);\n      setFlatPixelXY(flatMode,x,rows-1-py,pc,cols,rows,offset);\n    }\n'''
new='''    uint16_t h=(st->level[band]+254U)/255U;\n    if(h>rows) h=rows;\n    for(uint16_t y=0;y<h;y++){\n      // 8-row Technics layout: bottom 3 green, middle 3 yellow, top 2 red.\n      uint32_t c;\n      if(rows==8) c=(y<3)?GREEN:((y<6)?YELLOW:RED);\n      else { uint16_t z=(uint32_t)y*8U/max((uint16_t)1,rows); c=(z<3)?GREEN:((z<6)?YELLOW:RED); }\n      setFlatPixelXY(flatMode,x,rows-1-y,c,cols,rows,offset);\n    }\n\n    // Peak marker uses the color of the row it is currently holding.\n    if(st->peak[band]>0) {\n      uint16_t py=(st->peak[band]-1U)/255U;\n      if(py>=rows) py=rows-1;\n      uint32_t pc;\n      if(rows==8) pc=(py<3)?GREEN:((py<6)?YELLOW:RED);\n      else { uint16_t z=(uint32_t)py*8U/max((uint16_t)1,rows); pc=(z<3)?GREEN:((z<6)?YELLOW:RED); }\n      setFlatPixelXY(flatMode,x,rows-1-py,pc,cols,rows,offset);\n    }\n'''
fx=once(fx,old,new,'classic row colors')
fx=fx.replace('GEQ 32 HiFi ☾@Fall speed,Peak hold,# of bands,,,Level colors,Unused ☾;',
              'GEQ 32 Classic ☾@Fall speed,Peak hold,# of bands;;;;;2v;',1)

# ---------------------------------------------------------------------------
# Four extra effects. All prefer UM slot 12 = real 32-band local FFT and only
# fall back to interpolated 16-band data for AudioSync/legacy sources.
# ---------------------------------------------------------------------------
marker='''static const char _data_FX_MODE_2DGEQ[] PROGMEM = "GEQ 32 Classic ☾@Fall speed,Peak hold,# of bands;;;;;2v;'''
pos=fx.find(marker)
if pos<0: raise SystemExit('GEQ data marker not found')
line_end=fx.find('\n',pos)
if line_end<0: raise SystemExit('GEQ data line end not found')
line_end+=1

extra=r'''

// ---------------------------------------------------------------------------
// Custom true-32-band helpers/effects for a 32x8 matrix.
// ---------------------------------------------------------------------------
static inline void geq32GetBands(uint8_t out[32]) {
  memset(out,0,32);
  um_data_t *u=getAudioData();
  if(u && u->u_data && u->u_size>12 && u->u_data[12]) {
    memcpy(out,u->u_data[12],32);
  } else if(u && u->u_data && u->u_data[2]) {
    uint8_t *q=(uint8_t*)u->u_data[2];
    for(uint8_t i=0;i<32;i++) {
      uint8_t a=i>>1,b=min((uint8_t)(a+1),(uint8_t)15);
      out[i]=(i&1)?(uint8_t)(((uint16_t)q[a]+q[b])>>1):q[a];
    }
  }
}

static inline uint8_t geq32BandForX(uint16_t x,uint16_t cols) {
  if(cols<=1) return 0;
  if(cols==32) return constrain((int)x,0,31);
  return constrain((int)map(x,0,cols-1,0,31),0,31);
}

static inline uint32_t geq32RowColor(uint16_t yFromBottom,uint16_t rows) {
  if(rows==8) return (yFromBottom<3)?GREEN:((yFromBottom<6)?YELLOW:RED);
  uint16_t z=(uint32_t)yFromBottom*8U/max((uint16_t)1,rows);
  return (z<3)?GREEN:((z<6)?YELLOW:RED);
}

// 32 bands mirrored around the horizontal center line.
uint16_t mode_GEQ32Center(void) {
  if(!SEGMENT.is2D()) return mode_oops();
  const uint16_t cols=SEGMENT.virtualWidth(), rows=SEGMENT.virtualHeight();
  if(cols<2||rows<2) return mode_oops();
  uint8_t v[32]; geq32GetBands(v);
  SEGMENT.fill(BLACK);
  const uint16_t lower=rows/2, upper=rows-lower;
  const uint16_t half=max((uint16_t)1,min(lower,upper));
  for(uint16_t x=0;x<cols;x++) {
    uint8_t b=geq32BandForX(x,cols);
    uint16_t h=((uint32_t)v[b]*half+254U)/255U;
    if(h>half) h=half;
    for(uint16_t d=0;d<h;d++) {
      uint32_t c=geq32RowColor(d*2,8); // green near center, yellow/red toward edge
      if(lower>d) SEGMENT.setPixelColorXY(x,lower-1-d,c);
      if(lower+d<rows) SEGMENT.setPixelColorXY(x,lower+d,c);
    }
  }
  return FRAMETIME;
}
static const char _data_FX_MODE_GEQ32CENTER[] PROGMEM = "GEQ 32 Center@!;;;;;!;2v";

// Falling peak dots only. Speed controls drop rate.
uint16_t mode_GEQ32Peaks(void) {
  if(!SEGMENT.is2D()) return mode_oops();
  const uint16_t cols=SEGMENT.virtualWidth(), rows=SEGMENT.virtualHeight();
  if(cols<2||rows<2) return mode_oops();
  struct D { uint16_t p[32]; uint32_t last; };
  if(!SEGENV.allocateData(sizeof(D))) return mode_oops();
  D *st=(D*)SEGENV.data;
  if(SEGENV.call==0){memset(st,0,sizeof(D));st->last=strip.now;}
  uint32_t dt=strip.now-st->last; if(dt<1)dt=1; if(dt>100)dt=100; st->last=strip.now;
  const uint16_t fall=max((uint16_t)1,(uint16_t)(((700U+(uint32_t)SEGMENT.speed*6500U/255U)*dt)/1000U));
  uint8_t v[32]; geq32GetBands(v);
  for(uint8_t i=0;i<32;i++) {
    uint16_t t=(uint32_t)v[i]*rows*255U/255U;
    if(t>=st->p[i]) st->p[i]=t;
    else st->p[i]=(st->p[i]>fall)?st->p[i]-fall:0;
  }
  SEGMENT.fill(BLACK);
  for(uint16_t x=0;x<cols;x++) {
    uint8_t b=geq32BandForX(x,cols);
    if(st->p[b]) {
      uint16_t py=(st->p[b]-1U)/255U; if(py>=rows)py=rows-1;
      SEGMENT.setPixelColorXY(x,rows-1-py,geq32RowColor(py,rows));
    }
  }
  return FRAMETIME;
}
static const char _data_FX_MODE_GEQ32PEAKS[] PROGMEM = "GEQ 32 Peaks@Fall speed;;;;;!;2v";

// 8-row time history. Newest spectrum enters at the bottom and scrolls upward.
uint16_t mode_GEQ32Waterfall(void) {
  if(!SEGMENT.is2D()) return mode_oops();
  const uint16_t cols=SEGMENT.virtualWidth(), rows=SEGMENT.virtualHeight();
  if(cols<2||rows<2) return mode_oops();
  struct D { uint8_t h[8][32]; uint32_t last; };
  if(!SEGENV.allocateData(sizeof(D))) return mode_oops();
  D *st=(D*)SEGENV.data;
  if(SEGENV.call==0){memset(st,0,sizeof(D));st->last=0;SEGMENT.fill(BLACK);}
  uint16_t interval=35U+((uint32_t)(255-SEGMENT.speed)*165U/255U);
  if(st->last==0 || strip.now-st->last>=interval) {
    st->last=strip.now;
    for(int y=7;y>0;y--) memcpy(st->h[y],st->h[y-1],32);
    geq32GetBands(st->h[0]);
  }
  SEGMENT.fill(BLACK);
  const uint16_t showRows=min((uint16_t)8,rows);
  for(uint16_t y=0;y<showRows;y++) for(uint16_t x=0;x<cols;x++) {
    uint8_t b=geq32BandForX(x,cols), a=st->h[y][b];
    if(a<4) continue;
    uint32_t base=(a<86)?GREEN:((a<171)?YELLOW:RED);
    uint32_t c=color_blend(BLACK,base,a);
    SEGMENT.setPixelColorXY(x,rows-1-y,c);
  }
  return FRAMETIME;
}
static const char _data_FX_MODE_GEQ32WATERFALL[] PROGMEM = "GEQ 32 Waterfall@Scroll speed;;;;;!;2v";

// Oscilloscope-like frequency trace. One point per band with persistence.
uint16_t mode_GEQ32Trace(void) {
  if(!SEGMENT.is2D()) return mode_oops();
  const uint16_t cols=SEGMENT.virtualWidth(), rows=SEGMENT.virtualHeight();
  if(cols<2||rows<2) return mode_oops();
  SEGMENT.fadeToBlackBy(80U+((uint32_t)(255-SEGMENT.intensity)*150U/255U));
  uint8_t v[32]; geq32GetBands(v);
  for(uint16_t x=0;x<cols;x++) {
    uint8_t b=geq32BandForX(x,cols);
    uint16_t h=((uint32_t)v[b]*(rows-1)+127U)/255U;
    if(h>=rows)h=rows-1;
    SEGMENT.setPixelColorXY(x,rows-1-h,geq32RowColor(h,rows));
  }
  return FRAMETIME;
}
static const char _data_FX_MODE_GEQ32TRACE[] PROGMEM = "GEQ 32 Trace@!,Persistence;;;;;!;2v";
'''
fx=fx[:line_end]+extra+fx[line_end:]

# Register them right next to the stock/custom GEQ entry.
old='''  addEffect(FX_MODE_2DGEQ, &mode_2DGEQ, _data_FX_MODE_2DGEQ); // audio\n'''
new='''  addEffect(FX_MODE_2DGEQ, &mode_2DGEQ, _data_FX_MODE_2DGEQ); // audio\n  addEffect(FX_MODE_GEQ32CENTER, &mode_GEQ32Center, _data_FX_MODE_GEQ32CENTER);\n  addEffect(FX_MODE_GEQ32PEAKS, &mode_GEQ32Peaks, _data_FX_MODE_GEQ32PEAKS);\n  addEffect(FX_MODE_GEQ32WATERFALL, &mode_GEQ32Waterfall, _data_FX_MODE_GEQ32WATERFALL);\n  addEffect(FX_MODE_GEQ32TRACE, &mode_GEQ32Trace, _data_FX_MODE_GEQ32TRACE);\n'''
fx=once(fx,old,new,'effect registration')

fxp.write_text(fx,encoding='utf-8',newline='\n')
hp.write_text(h,encoding='utf-8',newline='\n')
print('Added GEQ 32 Classic colors + Center, Peaks, Waterfall and Trace effects')
