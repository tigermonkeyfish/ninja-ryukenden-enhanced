// Minimal in-process Geargrafx core for fast route search (diagnostic tool).
#include "geargrafx.h"
#include <cstring>
bool g_mcp_stdio_mode = true;
static GeargrafxCore* core = nullptr;
static u8* fb = nullptr;
static s16 samples[GG_AUDIO_BUFFER_SIZE * 4];
static u16 held = 0;
static void pump() {}
extern "C" {
int gx_init(const char* rom) {
    if (!core) { core = new GeargrafxCore(); core->Init(pump, GG_PIXEL_RGBA8888); fb = new u8[2048 * 512 * 4]; }
    return core->LoadMedia(rom) ? 1 : 0;
}
int gx_load_state(const u8* buf, size_t size) { return core->LoadState(buf, size) ? 1 : 0; }
size_t gx_state_size() { size_t s = 0; core->SaveState(NULL, s); return s; }
size_t gx_save_state(u8* buf, size_t size) { if (!core->SaveState(buf, size)) return 0; return size; }
void gx_set_buttons(int mask) {
    for (int b = 0; b < 8; b++) {
        u16 k = 1 << b;
        if ((mask & k) && !(held & k)) core->KeyPressed(GG_CONTROLLER_1, (GG_Keys)k);
        if (!(mask & k) && (held & k)) core->KeyReleased(GG_CONTROLLER_1, (GG_Keys)k);
    }
    held = mask;
}
void gx_reset_held() { held = 0; }
int gx_run(int frames, int render) {
    int n = 0;
    for (int i = 0; i < frames; i++) { int sc = 0; core->RunToVBlank(fb, samples, &sc, NULL, render != 0); n++; }
    return n;
}
u8* gx_wram() { return core->GetMemory()->GetWorkingRAM(); }
u8* gx_bram() { return core->GetMemory()->GetBackupRAM(); }
u8* gx_fb() { return fb; }
void gx_fb_size(int* w, int* h) { GG_Runtime_Info ri; core->GetRuntimeInfo(ri); *w = ri.screen_width; *h = ri.screen_height; }
}
