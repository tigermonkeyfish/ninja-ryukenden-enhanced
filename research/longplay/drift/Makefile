# Tracer core: the longplay fast core's objects (research/longplay/fast/Makefile, built in
# /workspace/build/longplay/fastemu/o with the same flags) plus shim_trace.cpp.
G=/workspace/build/toolchain/geargrafx
S=$(G)/src
D=$(G)/platforms/shared/dependencies
O=/workspace/build/longplay/fastemu/o
FL=-DGG_DISABLE_DISASSEMBLER -O3 -march=native -flto=auto -fPIC -DNDEBUG -fno-exceptions -DEMULATOR_BUILD=\"shim\" -DZ7_ST -DZSTD_DISABLE_ASM -w
INC=-I$(S) -I$(D)/libchdr/include -I$(D)/lzma/include -I$(D)/minivorbis -I$(D)/miniz -I$(D)/zstd
libgxt.so: shim_trace.o
	g++ -O3 -march=native -flto=auto -shared -o $@ $(filter-out $(O)/shim.o,$(wildcard $(O)/*.o)) shim_trace.o -lpthread
shim_trace.o: shim_trace.cpp
	g++ $(FL) $(INC) -std=c++11 -c -o $@ $<

# palette-exact: libgxw.so, the tracer plus a RAM access watch (shim_watch.cpp) and power-on with
# forced backup RAM. Its core is a private copy of the Geargrafx source (W) whose memory_inline.h
# calls gw_hook from Memory::Read / Memory::Write for RAM offsets in [gw_lo, gw_hi) (two lines:
# see palette-exact.md); every object is rebuilt from that copy.
W=/workspace/build/palette-exact/ggw/src
WO=/workspace/build/palette-exact/ggw/o
WCXX=geargrafx_core adpcm audio arcade_card_mapper cdrom_audio cdrom_chd_file_adapter cdrom_chd_image cdrom_cuebin_image media_file media_file_native ogg_vorbis_decoder cdrom_image cdrom_media cdrom huc6202 huc6260 huc6270 huc6280 huc6280_functors huc6280_opcodes huc6280_psg input mapper mb128 media memory scsi_controller sf2_mapper trace_logger turbolink vgm_recorder
WINC=-I$(W) -I$(D)/libchdr/include -I$(D)/lzma/include -I$(D)/minivorbis -I$(D)/miniz -I$(D)/zstd
WOBJ=$(addprefix $(WO)/,$(addsuffix .o,$(WCXX)))
watch: libgxw.so
$(WO)/%.o: $(W)/%.cpp
	@mkdir -p $(WO); g++ $(FL) $(WINC) -std=c++11 -c -o $@ $<
$(WO)/shim_watch.o: shim_watch.cpp
	@mkdir -p $(WO); g++ $(FL) $(WINC) -std=c++11 -c -o $@ $<
libgxw.so: $(WOBJ) $(WO)/shim_watch.o
	g++ -O3 -march=native -flto=auto -shared -o $@ $(WOBJ) $(wildcard $(O)/c_*.o) $(WO)/shim_watch.o -lpthread
