"""Make a test-only Geargrafx variant that models the backup RAM lock.

The project's emulator (Geargrafx 78fc3d7 with the headless patch) does not
decode $1807/$1803 for a HuCard: backup RAM, when the machine has it, is
always unlocked, so the game's unlock and lock cannot be tested there. This
script edits a COPY of that source tree (never the project's own) so that
the environment variable NG_BRAM_MODEL selects, for HuCards:

  lock      as the MiSTer core does it (rtl/cd/cd.vhd, rtl/pce_top.vhd):
            locked at reset; a write to $1807 unlocks when bit 7 is set and
            locks when it is clear; a read of $1803 locks. Locked, bank $F7
            reads $FF and ignores writes.
  key       the same, but only the three writes $48, $75, $80 in a row
            unlock (what the Tennokoe 2 is said to want); other writes
            leave the lock as it is.
  readonly  as lock, but writes never reach the memory (a save that cannot
            be stored).
  openbus   no backup RAM: bank $F7 reads the high byte of the address read
            (what a bus that keeps its last value gives an absolute read)
            and ignores writes.

Unset, the variant behaves like the project's build. The harness installs an
image as usual (emulator_session.power_on); the lock state is not part of a
save state and survives a state load.

usage: locktest_patch.py GEARGRAFX-COPY     (then: make -C platforms/linux)
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])


def edit(name, pairs):
    path = root / name
    text = path.read_text()
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f'{name}: expected one place for {old!r}, found {text.count(old)}')
        text = text.replace(old, new)
    path.write_text(text)


edit('src/memory.h', [
    ('''    bool m_backup_ram_enabled;
''', '''    bool m_backup_ram_enabled;
    // Test-only backup RAM models (NG_BRAM_MODEL): 0 none, 1 lock, 2 key,
    // 3 open bus, 4 read-only.
    int m_bram_model = 0;
    bool m_bram_unlocked = false;
    int m_bram_key = 0;
    void BramControlWrite(u8 value);
    void BramLockRead();
    void ApplyBramLock();
'''),
])

edit('src/memory.cpp', [
    ('''    memset(m_backup_ram, 0xFF, 0x2000);
    memset(m_backup_ram, 0x00, 0x800);
''', '''    {
        const char* model = getenv("NG_BRAM_MODEL");
        m_bram_model = 0;
        if (model && !strcmp(model, "lock")) m_bram_model = 1;
        if (model && !strcmp(model, "key")) m_bram_model = 2;
        if (model && !strcmp(model, "openbus")) m_bram_model = 3;
        if (model && !strcmp(model, "readonly")) m_bram_model = 4;
        m_bram_unlocked = false;
        m_bram_key = 0;
    }
    memset(m_backup_ram, 0xFF, 0x2000);
    memset(m_backup_ram, 0x00, 0x800);
'''),
    ('''void Memory::SaveRam(std::ostream &file)
''', '''void Memory::ApplyBramLock()
{
    if (m_bram_model == 1 || m_bram_model == 2 || m_bram_model == 4)
        UpdateBackupRam(m_bram_unlocked);
}

void Memory::BramControlWrite(u8 value)
{
    if (m_bram_model == 2)
    {
        static const u8 key[3] = { 0x48, 0x75, 0x80 };
        if (value == key[m_bram_key])
        {
            if (++m_bram_key == 3)
            {
                m_bram_unlocked = true;
                m_bram_key = 0;
            }
        }
        else
            m_bram_key = (value == key[0]) ? 1 : 0;
    }
    else
        m_bram_unlocked = (value & 0x80) != 0;
    ApplyBramLock();
}

void Memory::BramLockRead()
{
    m_bram_unlocked = false;
    m_bram_key = 0;
    ApplyBramLock();
}

void Memory::SaveRam(std::ostream &file)
'''),
])

text = (root / 'src/memory.cpp').read_text()
if text.count('    ReloadMemoryMap();\n}\n\nvoid Memory::ReloadMemoryMap()') != 1:
    raise SystemExit('memory.cpp: Reset/ReloadMemoryMap not as expected')
# The lock applies whenever the map is rebuilt (reset, state load).
marker = 'void Memory::ReloadMemoryMap()\n{\n'
start = text.index(marker)
end = text.index('\n}\n', start)
text = text[:end] + '\n\n    ApplyBramLock();' + text[end:]
if '#include <cstring>' not in text:
    text = '#include <cstring>\n#include <cstdlib>\n' + text
(root / 'src/memory.cpp').write_text(text)

edit('src/memory_inline.h', [
    ('''    if (bank != 0xFF)
    {
        if (IsValidPointer(m_current_mapper) && (bank < 0x80))
            return m_current_mapper->Read(bank, offset);
''', '''    if (bank != 0xFF)
    {
        if (bank == 0xF7 && m_bram_model == 3)
            return (u8)(address >> 8);
        if (IsValidPointer(m_current_mapper) && (bank < 0x80))
            return m_current_mapper->Read(bank, offset);
'''),
    ('''                        return m_cdrom->ReadRegister(offset);
                }
                else
                    return 0xFF;
''', '''                        return m_cdrom->ReadRegister(offset);
                }
                else
                {
                    if (m_bram_model != 0 && m_bram_model != 3 && (offset & 0x1F0F) == 0x1803)
                        BramLockRead();
                    return 0xFF;
                }
'''),
    ('''        if (m_memory_map_write[bank] && (offset < 0x800))
            m_memory_map[bank][offset] = value;
''', '''        if (m_memory_map_write[bank] && (offset < 0x800) && m_bram_model != 4)
            m_memory_map[bank][offset] = value;
'''),
    ('''                        m_cdrom->WriteRegister(offset, value);
                }
                break;
''', '''                        m_cdrom->WriteRegister(offset, value);
                }
                else if (m_bram_model != 0 && m_bram_model != 3 && (offset & 0x1F0F) == 0x1807)
                    BramControlWrite(value);
                break;
'''),
])
print('patched', root)
