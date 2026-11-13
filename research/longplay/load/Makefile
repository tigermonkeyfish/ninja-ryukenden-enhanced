# load-exact: libgxl.so = the palette-exact watch core (research/longplay/drift, target watch:
# objects in /workspace/build/palette-exact/ggw/o) plus shim_load.cpp (shim_watch.cpp with
# VRAM / VCE / frame-buffer exports). Build `make -C ../drift watch` first.
G=/workspace/build/toolchain/geargrafx
D=$(G)/platforms/shared/dependencies
O=/workspace/build/longplay/fastemu/o
W=/workspace/build/palette-exact/ggw/src
WO=/workspace/build/palette-exact/ggw/o
OUT=/workspace/build/load-exact/lib
FL=-DGG_DISABLE_DISASSEMBLER -O3 -march=native -flto=auto -fPIC -DNDEBUG -fno-exceptions -DEMULATOR_BUILD=\"shim\" -DZ7_ST -DZSTD_DISABLE_ASM -w
WINC=-I$(W) -I$(D)/libchdr/include -I$(D)/lzma/include -I$(D)/minivorbis -I$(D)/miniz -I$(D)/zstd
WCXX=geargrafx_core adpcm audio arcade_card_mapper cdrom_audio cdrom_chd_file_adapter cdrom_chd_image cdrom_cuebin_image media_file media_file_native ogg_vorbis_decoder cdrom_image cdrom_media cdrom huc6202 huc6260 huc6270 huc6280 huc6280_functors huc6280_opcodes huc6280_psg input mapper mb128 media memory scsi_controller sf2_mapper trace_logger turbolink vgm_recorder
WOBJ=$(addprefix $(WO)/,$(addsuffix .o,$(WCXX)))
$(OUT)/libgxl.so: $(OUT)/shim_load.o
	g++ -O3 -march=native -flto=auto -shared -o $@ $(WOBJ) $(wildcard $(O)/c_*.o) $(OUT)/shim_load.o -lpthread
$(OUT)/shim_load.o: shim_load.cpp
	@mkdir -p $(OUT); g++ $(FL) $(WINC) -std=c++11 -c -o $@ $<
