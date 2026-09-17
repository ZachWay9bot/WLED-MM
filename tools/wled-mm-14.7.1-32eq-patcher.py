#!/usr/bin/env python3
# WLED-MM v14.7.1 32-band GEQ patcher
# Keeps legacy 16-band effects and UDP AudioSync intact.

from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
AR = ROOT / "usermods" / "audioreactive" / "audio_reactive.h"
FX = ROOT / "wled00" / "FX.cpp"

def die(msg):
    raise SystemExit("ERROR: " + msg)

def replace_once(s, old, new, desc):
    n = s.count(old)
    if n != 1:
        die(f"{desc}: expected exactly 1 match, got {n}")
    return s.replace(old, new, 1)

if not AR.exists() or not FX.exists():
    die("Run from a WLED-MM v14.7.1 source tree, or pass its path as argument.")

ar = AR.read_text(encoding="utf-8")
fx = FX.read_text(encoding="utf-8")

if "#define NUM_GEQ_CHANNELS 16" not in ar:
    die("audio_reactive.h is not the expected v14.7.1 baseline.")
if "const int NUM_BANDS = map2(SEGMENT.custom1, 0, 255, 1, 16);" not in fx:
    die("FX.cpp is not the expected v14.7.1 baseline.")

old = '''static uint8_t fftResult[NUM_GEQ_CHANNELS]= {0};   // Our calculated freq. channel result table to be used by effects
static float   fftCalc[NUM_GEQ_CHANNELS] = {0.0f}; // Try and normalize fftBin values to a max of 4096, so that 4096/16 = 256. (also used by dynamics limiter)
static float   fftAvg[NUM_GEQ_CHANNELS] = {0.0f};  // Calculated frequency channel results, with smoothing (used if dynamics limiter is ON)
'''
new = old + '''
// WLED-MM 14.7.1 / 32EQ extension.
// Keep legacy 16 channels intact: AudioSync v2 and existing effects depend on them.
#define NUM_GEQ_CHANNELS_32 32
static uint8_t fftResult32[NUM_GEQ_CHANNELS_32] = {0};
static float   fftCalc32[NUM_GEQ_CHANNELS_32]   = {0.0f};
static float   fftAvg32[NUM_GEQ_CHANNELS_32]    = {0.0f};

static constexpr uint16_t fft32Edges[NUM_GEQ_CHANNELS_32 + 1] = {
   1,  2,  3,  4,  5,  6,  7,  8,
   9, 10, 11, 12, 13, 15, 17, 20,
  23, 26, 30, 35, 40, 46, 53, 61,
  70, 81, 93,107,123,142,163,188,216
};
'''
ar = replace_once(ar, old, new, "insert 32-band state")

old = '''static void postProcessFFTResults(bool noiseGateOpen, int numberOfChannels, bool i2sFastpath); // post-processing and post-amp of GEQ channels
'''
new = old + '''static void build32BandGEQ(float windowCorrection, bool noiseGateOpen); // independent 32-band path for GEQ
'''
ar = replace_once(ar, old, new, "insert 32-band prototype")

marker = '''static void postProcessFFTResults(bool noiseGateOpen, int numberOfChannels, bool i2sFastpath) // post-processing and post-amp of GEQ channels
{
'''
helper = r'''// WLED-MM 14.7.1 / 32EQ
static inline float pinkFactor32(uint8_t profile, uint8_t band)
{
  if (profile > MAX_PINK) profile = MAX_PINK;
  const float pos = (float(band) * float(NUM_GEQ_CHANNELS - 1)) / float(NUM_GEQ_CHANNELS_32 - 1);
  const uint8_t lo = (uint8_t)pos;
  const uint8_t hi = min((uint8_t)(lo + 1), (uint8_t)(NUM_GEQ_CHANNELS - 1));
  const float frac = pos - float(lo);
  return fftResultPink[profile][lo] + frac * (fftResultPink[profile][hi] - fftResultPink[profile][lo]);
}

static void build32BandGEQ(float windowCorrection, bool noiseGateOpen)
{
  static uint32_t lastUpdate = 0;
  const uint32_t now = millis();
  uint32_t dt = (lastUpdate == 0) ? 23 : (now - lastUpdate);
  lastUpdate = now;
  dt = constrain(dt, (uint32_t)1, (uint32_t)1000);

  const float maxAttack = (attackTime == 0) ? 1023.0f : (1023.0f * float(dt) / float(attackTime));
  const float maxDecay  = (decayTime  == 0) ? -1023.0f : (-1023.0f * float(dt) / float(decayTime));

  for (uint8_t i = 0; i < NUM_GEQ_CHANNELS_32; i++) {
    if (noiseGateOpen) {
      const int firstBin = fft32Edges[i];
      const int lastBin  = fft32Edges[i + 1] - 1;
      float v = windowCorrection * fftAddAvg(firstBin, lastBin);

      v *= pinkFactor32(pinkIndex, i);
      if (FFTScalingMode > 0) v *= FFT_DOWNSCALE;
      v *= soundAgc
        ? multAgc
        : ((float)sampleGain / 40.0f * (float)inputLevel / 128.0f + 1.0f / 16.0f);

      fftCalc32[i] = constrain(v, 0.0f, 1023.0f);
    } else {
      fftCalc32[i] *= 0.85f;
      if (fftCalc32[i] < 4.0f) fftCalc32[i] = 0.0f;
    }

    if (limiterOn) {
      float delta = fftCalc32[i] - fftAvg32[i];
      if (delta > maxAttack) delta = maxAttack;
      if (delta < maxDecay)  delta = maxDecay;
      fftAvg32[i] = constrain(fftAvg32[i] + delta, 0.0f, 1023.0f);
    } else {
      fftAvg32[i] = fftCalc32[i];
    }

    float currentResult = limiterOn ? fftAvg32[i] : fftCalc32[i];

    switch (FFTScalingMode) {
      case 1:
        currentResult *= 0.42f;
        currentResult -= 8.0f;
        currentResult = (currentResult > 1.0f) ? logf(currentResult) : 0.0f;
        currentResult *= 0.85f + (float(i) / 36.0f);
        currentResult = mapf(currentResult, 0.0f, LOG_256, 0.0f, 255.0f);
        break;
      case 2:
        currentResult *= 0.30f;
        currentResult -= 2.0f;
        if (currentResult < 1.0f) currentResult = 0.0f;
        currentResult *= 0.85f + (float(i) / 3.6f);
        break;
      case 3:
        currentResult *= 0.38f;
        currentResult -= 6.0f;
        currentResult = (currentResult > 1.0f) ? sqrtf(currentResult) : 0.0f;
        currentResult *= 0.85f + (float(i) / 9.0f);
        currentResult = mapf(currentResult, 0.0f, 16.0f, 0.0f, 255.0f);
        break;
      default:
        currentResult -= 2.0f;
        break;
    }

    if (soundAgc > 0) {
      float postGain = (float)inputLevel / 128.0f;
      if (postGain < 1.0f) postGain = ((postGain - 1.0f) * 0.8f) + 1.0f;
      currentResult *= postGain;
    }
    fftResult32[i] = (uint8_t)constrain((int)(currentResult + 0.5f), 0, 255);
  }
}

''' + marker
ar = replace_once(ar, marker, helper, "insert 32-band processor")

old = '''    // post-processing of frequency channels (pink noise adjustment, AGC, smoothing, scaling)
    if (pinkIndex > MAX_PINK) pinkIndex = MAX_PINK;

#ifdef FFT_USE_SLIDING_WINDOW
'''
new = '''    // post-processing of frequency channels (pink noise adjustment, AGC, smoothing, scaling)
    if (pinkIndex > MAX_PINK) pinkIndex = MAX_PINK;

    build32BandGEQ(wc, (fabsf(volumeSmth) > 0.25f));

#ifdef FFT_USE_SLIDING_WINDOW
'''
ar = replace_once(ar, old, new, "call 32-band processor")

old = '''      memset(fftCalc, 0, sizeof(fftCalc)); 
      memset(fftAvg, 0, sizeof(fftAvg)); 
      memset(fftResult, 0, sizeof(fftResult)); 
'''
new = old + '''      memset(fftCalc32, 0, sizeof(fftCalc32));
      memset(fftAvg32, 0, sizeof(fftAvg32));
      memset(fftResult32, 0, sizeof(fftResult32));
'''
ar = replace_once(ar, old, new, "reset 32-band state")

ar = replace_once(ar, "um_data->u_size = 12;", "um_data->u_size = 13;", "grow UM data table")

old = '''        um_data->u_data[2] = fftResult;        //*used (Blurz, DJ Light, Noisemove, GEQ_base, 2D Funky Plank, Akemi)
        um_data->u_type[2] = UMT_BYTE_ARR;
'''
new = old + '''        um_data->u_data[12] = fftResult32;
        um_data->u_type[12] = UMT_BYTE_ARR;
'''
ar = replace_once(ar, old, new, "export 32-band UM data")

start = fx.find("uint16_t mode_2DGEQ(void)")
end = fx.find('static const char _data_FX_MODE_2DGEQ[]', start)
if start < 0 or end < 0:
    die("Could not locate mode_2DGEQ() in FX.cpp")
geq = fx[start:end]

geq = geq.replace(
    "const int NUM_BANDS = map2(SEGMENT.custom1, 0, 255, 1, 16);",
    "const int NUM_BANDS = map2(SEGMENT.custom1, 0, 255, 1, 32);"
)

old_geq_buf = '''  uint8_t fftResult[NUM_GEQ_CHANNELS] = {0};
  if (um_data->u_data != nullptr) memcpy(fftResult, um_data->u_data[2], sizeof(fftResult));  // WLEDMM buffer curent values
'''
new_geq_buf = '''  uint8_t fftResult32[32] = {0};
  if ((um_data->u_data != nullptr) && (um_data->u_size > 12) && (um_data->u_data[12] != nullptr)) {
    memcpy(fftResult32, um_data->u_data[12], sizeof(fftResult32));
  } else if ((um_data->u_data != nullptr) && (um_data->u_data[2] != nullptr)) {
    uint8_t *legacy16 = (uint8_t*)um_data->u_data[2];
    for (uint8_t i = 0; i < 32; i++) {
      const uint8_t a = i >> 1;
      const uint8_t b = min((uint8_t)(a + 1), (uint8_t)15);
      fftResult32[i] = (i & 1)
        ? (uint8_t)((uint16_t(legacy16[a]) + legacy16[b]) >> 1)
        : legacy16[a];
    }
  }
'''
if old_geq_buf not in geq:
    die("Could not locate GEQ FFT buffer code")
geq = geq.replace(old_geq_buf, new_geq_buf, 1)

geq = geq.replace("NUM_BANDS < 16", "NUM_BANDS < 32")
geq = geq.replace("0, NUM_BANDS - 1, 0, 15", "0, NUM_BANDS - 1, 0, 31")
geq = geq.replace("constrain(nextband, 0, 15)", "constrain(nextband, 0, 31)")
geq = geq.replace("fftResult[frBand]", "fftResult32[frBand]")
geq = geq.replace(
    "uint16_t colorIndex = frBand * 17;",
    "uint16_t colorIndex = map(frBand, 0, 31, 0, 255);"
)

fx = fx[:start] + geq + fx[end:]
fx = fx.replace(
    '"GEQ ☾@Fade speed,Ripple decay,# of bands,,,Color bars,Smooth bars ☾;',
    '"GEQ 32 ☾@Fade speed,Ripple decay,# of bands,,,Color bars,Smooth bars ☾;',
    1
)

AR.write_text(ar, encoding="utf-8", newline="\n")
FX.write_text(fx, encoding="utf-8", newline="\n")

print("Patched successfully:")
print(" ", AR)
print(" ", FX)
print("Legacy 16-band AudioSync/effects remain unchanged.")
print("GEQ now accepts 1..32 bands.")
