#!/usr/bin/env python3
"""A stored run after a cold boot whose palette mode came from backup RAM
(research reference, not a maintained tool).

The machine is powered on with backup RAM holding one file, the game's own
settings entry with OPTIONS ($2100) and English. Controller input alone
takes it through the title into 1-1 (comparison_video.boot's presses); the
debugger never writes $2100: the reset loader of src/bram must have set it,
which is asserted, with the status OK and backup RAM unchanged. From the
main-loop hook the stage of the stored run is entered as every stored-run
probe enters it (comparison_video.start_stage, the Level Select's writes)
and the run is replayed and recorded by dark-lift/trans.py's Recorder, so
that transreport.py reads the result: record OPTIONS 0x00 as TAG-original
and a mapped mode as TAG-sms or TAG-hell, then
    transreport.py OUT TAG --modes sms,hell --all
lists every span in which Original's playfield is black with the mode's
late frames (tail), flash and entries lit at the load's lock.
usage: savedboot.py ROM OUT TAG-MODE OPTIONS RUN   (GB_WORK as trans.py;
the emulator from NG_EMULATOR; one session)"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'dark-lift'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
import trans  # noqa: E402
from gbtools import EMU, WORK, cv, load_run  # noqa: E402
import bram_image  # noqa: E402


def boot(game, rom, bram):
    """comparison_video.boot from a machine with backup RAM: the same
    presses, to the main-loop hook ($83F3) in 1-1."""
    game.power_on(rom, bram)
    game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    previous, since, presses, title_pressed = None, 0, [200], False
    for frame in range(1, 20000):
        game.step(1)
        since += 1
        status = game.call('debug_get_status')
        if status.get('at_breakpoint') and status['pc'] == '83F3':
            break
        master = game.read(0x240, 2)
        if master != previous:
            previous, since = master, 0
        if master == b'\x01\x01' and since == 180 and not title_pressed:
            presses.append(frame)
            title_pressed = True
        if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150:
            presses.append(frame)
        for p in presses:
            if frame == p:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'press'})
            elif frame == p + 2:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'release'})
    else:
        raise RuntimeError('Gameplay not reached')
    game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    game.step(120)
    game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    game.run_to('83F3')
    game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    return frame


def main():
    rom, out, tag, options, name = sys.argv[1], Path(sys.argv[2]), sys.argv[3], int(sys.argv[4], 0), sys.argv[5]
    out.mkdir(parents=True, exist_ok=True)
    image = bytes(bram_image.image([bram_image.settings_entry(options, 1)]))
    folder = Path(tempfile.mkdtemp(prefix='saved-', dir=WORK))
    rec = trans.Recorder(out, tag, f'run:{name}', options)
    try:
        with cv.Game(EMU, folder) as game:
            frames = boot(game, rom, image)
            ram = game.read(0, 0x2000)
            found = {'boot_frames': frames, 'options_$2100': f'${ram[0x100]:02X}', 'shadow_$2101': f'${ram[0x101]:02X}',
                     'language_$3227': ram[0x1227], 'status_$2105': bram_image.STATUS[ram[0x105]], 'stage': ram[0xe5f],
                     'backup_ram_unchanged': game.backup_ram() == image}
            print(tag, found, flush=True)
            assert ram[0x100] == options, 'the mode did not come from backup RAM'
            assert ram[0x1227] == 1 and ram[0x105] == bram_image.LOADED and found['backup_ram_unchanged'], found
            trans.run_case(game, rec, name)
            end = game.read(0, 0x2000)
            run = load_run(name)
            print(tag, {'run': name, 'entered_stage': run['stage'], 'stage_at_end': end[0xe5f], 'master_at_end': end[0x240],
                        'options_at_end': f'${end[0x100]:02X}', 'backup_ram_unchanged': game.backup_ram() == image},
                  flush=True)
            assert end[0x100] == options and game.backup_ram() == image
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    rec.close()


if __name__ == '__main__':
    main()
