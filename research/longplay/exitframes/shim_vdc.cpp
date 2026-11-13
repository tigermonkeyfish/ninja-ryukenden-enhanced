// Diagnostic in-process Geargrafx core with an instruction tracer (longplay drift).
// The run loop is RunToVBlankTemplate<debugger=true,false,false> with debug == NULL,
// copied verbatim, plus passive recording of (master clock, PC, bank) before each
// RunInstruction call. Recording reads state only.
#include <string>
#include <iostream>
#include <sstream>
#include <fstream>
#include <vector>
#include <map>
#include <list>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <algorithm>
#include <functional>
#include <mutex>
#include <atomic>
#include <thread>
#include "geargrafx.h"
// Standard-conforming access to private members (explicit instantiation ignores access).
template<typename Tag, typename Tag::type M> struct Rob { friend typename Tag::type get(Tag) { return M; } };
#define ROB(name, T, ...) struct name { typedef T type; friend type get(name); }; template struct Rob<name, __VA_ARGS__>;
ROB(R_clk, u64 GeargrafxCore::*, &GeargrafxCore::m_master_clock_cycles)
ROB(R_ready, bool GeargrafxCore::*, &GeargrafxCore::m_frame_ready)
ROB(R_cpu, HuC6280* GeargrafxCore::*, &GeargrafxCore::m_huc6280)
ROB(R_vce, HuC6260* GeargrafxCore::*, &GeargrafxCore::m_huc6260)
ROB(R_audio, Audio* GeargrafxCore::*, &GeargrafxCore::m_audio)
ROB(R_input, Input* GeargrafxCore::*, &GeargrafxCore::m_input)
ROB(R_mem, Memory* GeargrafxCore::*, &GeargrafxCore::m_memory)
typedef bool (GeargrafxCore::*CHT)(u32);
ROB(R_ch, CHT, &GeargrafxCore::ClockHardware<false, false>)
typedef void (*CBT)(void*, u32);
ROB(R_cb, CBT, &GeargrafxCore::ClockHardwareCallback<false, false>)
bool g_mcp_stdio_mode = true;
static GeargrafxCore* core = nullptr;
static u8* fb = nullptr;
static s16 samples[GG_AUDIO_BUFFER_SIZE * 4];
static u16 held = 0;
static void pump() {}
struct Rec { u64 clk; u16 pc; u8 bank; u8 done; u32 cyc; };
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
unsigned long long gx_clock() { return core->GetMasterClockCycles(); }
u8* gx_wram() { return core->GetMemory()->GetWorkingRAM(); }
u8* gx_bram() { return core->GetMemory()->GetBackupRAM(); }
u8* gx_rom() { return core->GetMedia()->GetROM(); }

// One frame, recording every RunInstruction call into rec (up to cap). Returns count
// (may exceed cap: then only cap were stored). Same loop as the debugger template.
long gx_trace_frame(Rec* rec, long cap) {
    GeargrafxCore* c = core;
        (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
    bool instruction_completed = false;
    (c->*get(R_cpu()))->SetDebugBRK(false, 0, false);
    (c->*get(R_vce()))->SetBuffer(NULL);
    bool stop = false;
    long n = 0;
    Memory* mem = (c->*get(R_mem()));
    do {
        u64 clk = (c->*get(R_clk()));
        u16 pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
        (c->*get(R_ready())) = false;
        u32 cycles = (c->*get(R_cpu()))->RunInstruction();
        u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
        u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
        stop = (c->*get(R_ready()));
        if ((c->*get(R_ch()))(remaining_cycles)) stop = true;
        if (n < cap) { rec[n].clk = clk; rec[n].pc = pc; rec[n].bank = mem->GetMpr(pc >> 13); rec[n].done = 1; rec[n].cyc = cycles; }
        n++;
    } while (!stop);
    { int sc = 0; (c->*get(R_audio()))->EndFrame(samples, &sc); }
    (c->*get(R_input()))->EndFrame();
    return n;
}

// Run frames recording hits on watched (bank<<16 | pc) keys: hit = {frame, key index, clock}.
struct Hit { u32 frame; u32 which; u64 clk; };
long gx_run_watch(int frames, const u32* keys, int nk, Hit* hits, long cap, const u8* buttons) {
    GeargrafxCore* c = core;
    long nh = 0;
    Memory* mem = (c->*get(R_mem()));
    for (int f = 0; f < frames; f++) {
        if (buttons) gx_set_buttons(buttons[f]);
        (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
        bool instruction_completed = false;
        (c->*get(R_cpu()))->SetDebugBRK(false, 0, false);
        (c->*get(R_vce()))->SetBuffer(NULL);
        bool stop = false;
        do {
            u16 pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
            u32 key = ((u32)mem->GetMpr(pc >> 13) << 16) | pc;
            for (int k = 0; k < nk; k++) if (keys[k] == key) { if (nh < cap) { hits[nh].frame = f; hits[nh].which = k; hits[nh].clk = (c->*get(R_clk())); } nh++; break; }
            (c->*get(R_ready())) = false;
            u32 cycles = (c->*get(R_cpu()))->RunInstruction();
            u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
            u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
            stop = (c->*get(R_ready()));
            if ((c->*get(R_ch()))(remaining_cycles)) stop = true;
        } while (!stop);
        int sc = 0;
        (c->*get(R_audio()))->EndFrame(samples, &sc);
        (c->*get(R_input()))->EndFrame();
    }
    return nh;
}
}
extern "C" {
// Run instructions until PC (with its bank) equals key, or max instructions pass.
// Returns instructions run, -1 on timeout. Diagnostic only: leaves the core mid-frame.
long gx_run_until(u32 key, long max) {
    GeargrafxCore* c = core;
    (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
    (c->*get(R_vce()))->SetBuffer(NULL);
    Memory* mem = (c->*get(R_mem()));
    for (long n = 0; n < max; n++) {
        u16 pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
        if ((((u32)mem->GetMpr(pc >> 13) << 16) | pc) == key && n > 0) return n;
        (c->*get(R_ready())) = false;
        u32 cycles = (c->*get(R_cpu()))->RunInstruction();
        u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
        u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
        (c->*get(R_ch()))(remaining_cycles);
        if ((c->*get(R_ready()))) { int sc = 0; (c->*get(R_audio()))->EndFrame(samples, &sc); (c->*get(R_input()))->EndFrame(); }
    }
    return -1;
}
}
extern "C" {
// One frame (same loop as gx_trace_frame); copies the 8 KiB RAM into buf the first time PC
// (with bank) equals key, and its clock into *clk. Returns 1 if snapped, 0 if not.
static int snap_nth = 1;
void gx_set_snap_nth(int n) { snap_nth = n; }
int gx_frame_snap(u32 key, u8* buf, unsigned long long* clk) {
    int hits = 0;
    GeargrafxCore* c = core;
    (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
    (c->*get(R_vce()))->SetBuffer(NULL);
    Memory* mem = (c->*get(R_mem()));
    bool stop = false; int snapped = 0;
    do {
        u16 pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
        if (!snapped && ((((u32)mem->GetMpr(pc >> 13) << 16) | pc) == key) && ++hits == snap_nth) { memcpy(buf, mem->GetWorkingRAM(), 0x2000); *clk = (c->*get(R_clk())); snapped = 1; }
        (c->*get(R_ready())) = false;
        u32 cycles = (c->*get(R_cpu()))->RunInstruction();
        u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
        u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
        stop = (c->*get(R_ready()));
        if ((c->*get(R_ch()))(remaining_cycles)) stop = true;
    } while (!stop);
    int sc = 0; (c->*get(R_audio()))->EndFrame(samples, &sc); (c->*get(R_input()))->EndFrame();
    return snapped;
}
}
// ---- palette-exact additions (shim_watch: build against a core copy whose Memory::Read and
// Memory::Write call gw_hook for RAM bank $F8 offsets in [gw_lo, gw_hi); see Makefile, target watch).
unsigned short gw_lo = 0, gw_hi = 0;
struct WRec { u32 frame; u16 off; u8 val; u8 w; u16 pc; u8 bank; u8 pad; u64 clk; };
static WRec* gw_buf = nullptr; static long gw_cap = 0, gw_n = 0; static u32 gw_frame = 0;
static u16 gw_pc = 0; static u8 gw_bank = 0; static int gw_writes_only = 1;
void gw_hook(unsigned short off, unsigned char v, int w) {
    if (gw_writes_only && !w) return;
    if (gw_n < gw_cap) { WRec& r = gw_buf[gw_n]; r.frame = gw_frame; r.off = off; r.val = v; r.w = (u8)w; r.pc = gw_pc; r.bank = gw_bank; r.pad = 0; r.clk = (core->*get(R_clk())); }
    gw_n++;
}
extern "C" {
// Power on with backup RAM forced and filled (bram may be NULL: none).
int gx_init_bram(const char* rom, const u8* bram, int n) {
    if (!core) { core = new GeargrafxCore(); core->Init(pump, GG_PIXEL_RGBA8888); fb = new u8[2048 * 512 * 4]; }
    core->GetMedia()->ForceBackupRAM(bram != NULL);
    if (!core->LoadMedia(rom)) return 0;
    if (bram) { u8* b = core->GetMemory()->GetBackupRAM(); if (!b) return 0; memcpy(b, bram, n); }
    return 1;
}
void gx_watch_range(int lo, int hi, int writes_only) { gw_lo = (u16)lo; gw_hi = (u16)hi; gw_writes_only = writes_only; }
// Run frames with buttons[f] (or none), recording watched RAM accesses into recs (up to cap).
// Returns the number of accesses (may exceed cap). frame numbers count from first_frame.
// Also records hits on watched (bank<<16 | pc) keys as gx_run_watch does (frame = first_frame + f);
// *nhits gets their count (may exceed hcap).
long gx_run_w(int frames, const u8* buttons, WRec* recs, long cap, u32 first_frame,
              const u32* keys, int nk, Hit* hits, long hcap, long* nhits) {
    GeargrafxCore* c = core;
    gw_buf = recs; gw_cap = cap; gw_n = 0;
    long nh = 0;
    Memory* mem = (c->*get(R_mem()));
    for (int f = 0; f < frames; f++) {
        gw_frame = first_frame + f;
        if (buttons) gx_set_buttons(buttons[f]);
        (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
        (c->*get(R_cpu()))->SetDebugBRK(false, 0, false);
        (c->*get(R_vce()))->SetBuffer(NULL);
        bool stop = false;
        do {
            gw_pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
            gw_bank = mem->GetMpr(gw_pc >> 13);
            if (nk) { u32 key = ((u32)gw_bank << 16) | gw_pc;
                for (int k = 0; k < nk; k++) if (keys[k] == key) { if (nh < hcap) { hits[nh].frame = first_frame + f; hits[nh].which = k; hits[nh].clk = (c->*get(R_clk())); } nh++; break; } }
            (c->*get(R_ready())) = false;
            u32 cycles = (c->*get(R_cpu()))->RunInstruction();
            u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
            u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
            stop = (c->*get(R_ready()));
            if ((c->*get(R_ch()))(remaining_cycles)) stop = true;
        } while (!stop);
        int sc = 0; (c->*get(R_audio()))->EndFrame(samples, &sc); (c->*get(R_input()))->EndFrame();
    }
    gw_buf = nullptr; gw_cap = 0;
    if (nhits) *nhits = nh;
    return gw_n;
}
}
// ---- load-exact additions: VRAM, VCE colour table, frame buffer.
extern "C" {
u16* gx_vram() { return core->GetHuC6270_1()->GetVRAM(); }
u16* gx_vce() { return core->GetHuC6260()->GetColorTable(); }
u8* gx_fb() { return fb; }
void gx_fb_size(int* w, int* h) { GG_Runtime_Info ri; core->GetRuntimeInfo(ri); *w = ri.screen_width; *h = ri.screen_height; }
}
// ---- exit-frames additions: VDC scroll-register writes and per-line latched scroll (state reads only).
ROB(V_ar, u16 HuC6270::*, &HuC6270::m_address_register)
typedef u16 (HuC6270::*RegArr)[20];
ROB(V_reg, RegArr, &HuC6270::m_register)
ROB(V_pend, bool HuC6270::*, &HuC6270::m_bg_scroll_y_update_pending)
ROB(V_vpos, s32 HuC6270::*, &HuC6270::m_vpos)
ROB(V_hpos, s32 HuC6270::*, &HuC6270::m_hpos)
ROB(V_rl, s32 HuC6270::*, &HuC6270::m_raster_line)
ROB(V_lbxr, u16 HuC6270::*, &HuC6270::m_latched_bxr)
ROB(V_boy, s32 HuC6270::*, &HuC6270::m_bg_offset_y)
struct VW { u32 frame; u16 pc; u8 bank; u8 reg; u16 val; u16 old; s16 vpos; s16 hpos; s16 raster; u8 op; u8 kind; u64 clk; };
struct LR { u32 frame; s16 vpos; u16 bxr; s32 by; s32 raster; };
extern "C" {
// Run frames like gx_run_w (RAM watch + key hits) and also record: every instruction that writes
// VDC BXR (reg 7) or BYR (reg 8) (kind 1 = value changed, 2 = BYR pending raised with the same
// value, 3 = st1/st2/sta to the data port with the register selected and no visible change), and
// per scanline the latched BXR and BG Y offset the line was drawn with (sampled when vpos advances).
long gx_run_vdc(int frames, const u8* buttons, WRec* recs, long cap, u32 first_frame,
                const u32* keys, int nk, Hit* hits, long hcap, long* nhits,
                VW* vw, long vcap, long* nvw, LR* lr, long lcap, long* nlr, int render) {
    GeargrafxCore* c = core;
    HuC6270* v = c->GetHuC6270_1();
    gw_buf = recs; gw_cap = cap; gw_n = 0;
    long nh = 0, nv = 0, nl = 0;
    Memory* mem = (c->*get(R_mem()));
    for (int f = 0; f < frames; f++) {
        gw_frame = first_frame + f;
        if (buttons) gx_set_buttons(buttons[f]);
        (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
        (c->*get(R_cpu()))->SetDebugBRK(false, 0, false);
        (c->*get(R_vce()))->SetBuffer(render ? fb : NULL);
        bool stop = false;
        s32 lastv = v->*get(V_vpos());
        do {
            gw_pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
            gw_bank = mem->GetMpr(gw_pc >> 13);
            if (nk) { u32 key = ((u32)gw_bank << 16) | gw_pc;
                for (int k = 0; k < nk; k++) if (keys[k] == key) { if (nh < hcap) { hits[nh].frame = first_frame + f; hits[nh].which = k; hits[nh].clk = (c->*get(R_clk())); } nh++; break; } }
            u16 ar = v->*get(V_ar());
            u16 r7 = (v->*get(V_reg()))[7], r8 = (v->*get(V_reg()))[8];
            bool pend = v->*get(V_pend());
            u8 op = mem->Read(gw_pc);
            u16 opnd = (u16)mem->Read(gw_pc + 1) | ((u16)mem->Read(gw_pc + 2) << 8);
            u64 clk0 = (c->*get(R_clk()));
            s16 vp0 = (s16)(v->*get(V_vpos())), hp0 = (s16)(v->*get(V_hpos())), rl0 = (s16)(v->*get(V_rl()));
            (c->*get(R_ready())) = false;
            u32 cycles = (c->*get(R_cpu()))->RunInstruction();
            u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
            u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
            u16 n7 = (v->*get(V_reg()))[7], n8 = (v->*get(V_reg()))[8];
            bool npend = v->*get(V_pend());
            bool port = (op == 0x13 || op == 0x23) || ((op == 0x8D || op == 0x8C || op == 0x8E || op == 0x9C) && (opnd == 2 || opnd == 3));
            int kind = 0; u8 reg = 0; u16 val = 0, old = 0;
            if (n7 != r7) { kind = 1; reg = 7; val = n7; old = r7; }
            else if (n8 != r8) { kind = 1; reg = 8; val = n8; old = r8; }
            else if (npend && !pend) { kind = 2; reg = 8; val = n8; old = r8; }
            else if (port && (ar == 7 || ar == 8)) { kind = 3; reg = (u8)ar; val = (v->*get(V_reg()))[ar]; old = val; }
            if (kind) { if (nv < vcap) { VW& w = vw[nv]; w.frame = first_frame + f; w.pc = gw_pc; w.bank = gw_bank; w.reg = reg; w.val = val; w.old = old;
                    w.vpos = vp0; w.hpos = hp0; w.raster = rl0; w.op = op; w.kind = (u8)kind; w.clk = clk0; } nv++; }
            stop = (c->*get(R_ready()));
            if ((c->*get(R_ch()))(remaining_cycles)) stop = true;
            s32 nvp = v->*get(V_vpos());
            if (nvp != lastv) {
                if (nl < lcap) { LR& l = lr[nl]; l.frame = first_frame + f; l.vpos = (s16)lastv; l.bxr = v->*get(V_lbxr()); l.by = v->*get(V_boy()); l.raster = v->*get(V_rl()); }
                nl++; lastv = nvp;
            }
        } while (!stop);
        int sc = 0; (c->*get(R_audio()))->EndFrame(samples, &sc); (c->*get(R_input()))->EndFrame();
    }
    gw_buf = nullptr; gw_cap = 0;
    if (nhits) *nhits = nh;
    *nvw = nv; *nlr = nl;
    return gw_n;
}
}
extern "C" {
// One frame, recording every instruction: clock, PC, bank, VDC vpos/hpos before it, P flags, opcode, cycles.
struct TR { u64 clk; u16 pc; u8 bank; u8 p; s16 vpos; s16 hpos; u8 op; u8 pad; u32 cyc; };
long gx_trace_vdc(TR* rec, long cap, int render) {
    GeargrafxCore* c = core;
    HuC6270* v = c->GetHuC6270_1();
    (c->*get(R_cpu()))->SetHardwareClock(get(R_cb()), c);
    (c->*get(R_cpu()))->SetDebugBRK(false, 0, false);
    (c->*get(R_vce()))->SetBuffer(render ? fb : NULL);
    Memory* mem = (c->*get(R_mem()));
    bool stop = false; long n = 0;
    do {
        u16 pc = (c->*get(R_cpu()))->GetState()->PC->GetValue();
        if (n < cap) { TR& r = rec[n]; r.clk = (c->*get(R_clk())); r.pc = pc; r.bank = mem->GetMpr(pc >> 13);
            r.p = (c->*get(R_cpu()))->GetState()->P->GetValue(); r.vpos = (s16)(v->*get(V_vpos())); r.hpos = (s16)(v->*get(V_hpos()));
            r.op = mem->Read(pc); r.pad = 0; }
        (c->*get(R_ready())) = false;
        u32 cycles = (c->*get(R_cpu()))->RunInstruction();
        u32 clocked_cycles = (c->*get(R_cpu()))->GetClockedMasterCycles();
        u32 remaining_cycles = (cycles > clocked_cycles) ? cycles - clocked_cycles : 0;
        if (n < cap) rec[n].cyc = cycles;
        stop = (c->*get(R_ready()));
        if ((c->*get(R_ch()))(remaining_cycles)) stop = true;
        n++;
    } while (!stop);
    int sc = 0; (c->*get(R_audio()))->EndFrame(samples, &sc); (c->*get(R_input()))->EndFrame();
    return n;
}
}
