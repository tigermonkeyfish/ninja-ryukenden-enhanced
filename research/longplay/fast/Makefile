G=/workspace/build/toolchain/geargrafx
S=$(G)/src
D=$(G)/platforms/shared/dependencies
CXXS=geargrafx_core adpcm audio arcade_card_mapper cdrom_audio cdrom_chd_file_adapter cdrom_chd_image cdrom_cuebin_image media_file media_file_native ogg_vorbis_decoder cdrom_image cdrom_media cdrom huc6202 huc6260 huc6270 huc6280 huc6280_functors huc6280_opcodes huc6280_psg input mapper mb128 media memory scsi_controller sf2_mapper trace_logger turbolink vgm_recorder
CS=$(D)/libchdr/src/libchdr_bitstream.c $(D)/libchdr/src/libchdr_cdrom.c $(D)/libchdr/src/libchdr_chd.c $(D)/libchdr/src/libchdr_flac.c $(D)/libchdr/src/libchdr_huffman.c $(D)/lzma/src/LzFind.c $(D)/lzma/src/LzmaEnc.c $(D)/lzma/src/LzmaDec.c $(D)/lzma/src/CpuArch.c $(D)/minivorbis/minivorbis.c $(D)/miniz/miniz.c
INC=-I$(S) -I$(D)/libchdr/include -I$(D)/lzma/include -I$(D)/minivorbis -I$(D)/miniz -I$(D)/zstd
FL=-O2 -fPIC -DNDEBUG -fno-exceptions -DEMULATOR_BUILD=\"shim\" -DZ7_ST -DZSTD_DISABLE_ASM -w
OBJ=$(addprefix o/,$(addsuffix .o,$(CXXS))) $(addprefix o/c_,$(notdir $(CS:.c=.o))) o/shim.o
all: libgx.so
o/%.o: $(S)/%.cpp
	@mkdir -p o; g++ $(FL) $(INC) -std=c++11 -c -o $@ $<
o/shim.o: shim.cpp
	@mkdir -p o; g++ $(FL) $(INC) -std=c++11 -c -o $@ $<
define CRULE
o/c_$(notdir $(1:.c=.o)): $(1)
	@mkdir -p o; gcc $(FL) $(INC) -std=gnu99 -c -o $$@ $$<
endef
$(foreach c,$(CS),$(eval $(call CRULE,$(c))))
libgx.so: $(OBJ)
	g++ -shared -o $@ $(OBJ) -lpthread
