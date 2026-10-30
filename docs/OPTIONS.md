# How to change the options

Ninja Ryukenden Enhanced has an in-game menu for **Level Select**,
**parallax** and **No Damage**. The language is changed on the title screen
with the original game's own switch.

When the console is switched on or reset, the game starts with these
defaults:

| Setting | Default | Where to change it |
| --- | --- | --- |
| Language | English | Title screen |
| Stage | 1-1 | In-game menu |
| Parallax | ON (Enhanced) | In-game menu |
| No Damage | OFF | In-game menu |

Settings are not saved. They return to these defaults after a reset or
power-off.

## Language

1. On the title screen (**PUSH RUN**), hold **I** and **II**.
2. While holding them, press **Select**. Each press switches to the next
   language: **English → Chinese → Japanese →** English. The line under the
   logo shows the current language.
3. Press **Run** to start the game.

![The title screen in English, Chinese and Japanese](images/options/title-languages.png)

The language is used for the story scenes and the game's text. Some title
and chapter artwork keeps its original Japanese lettering.

## The in-game menu

1. During play, press **Select**. The game pauses, and the menu replaces the
   status bar at the top of the screen (and the black line under it). The
   right column shows the patch version and the project's home,
   github.com/tigermonkeyfish:

   ```
   STAGE: 1-1      V1.10
   PARALLAX: ON    GITHUB.COM/
   NO DMG: OFF     TIGERMONKEYFISH
   RUN: ACCEPT     SELECT: CANCEL
   ```

   A gap in the middle leaves room for the held item's icon. The status bar
   returns when the menu closes.
2. Press **Up** or **Down** to choose a setting. The chosen setting's value
   blinks: **STAGE**, **PARALLAX** or **NO DMG**.
3. Press **Left** or **Right** to change it.
4. Press **Run** (**ACCEPT**) to apply your choices, or **Select**
   (**CANCEL**) to close the menu and keep playing with nothing changed.
   **I** and **II** do nothing in the menu.

![The menu, opened during 1-1](images/options/menu.png)

**Run** always restarts the stage shown in the menu from its beginning, even
when you changed only parallax or No Damage. Ryu's health is refilled and
the stage timer starts again from full; your score and lives carry over.

### Level Select (stage jump)

With **STAGE** chosen, press **Left** or **Right** to step through the
stages: 1-1, 1-2, 2-1 and so on up to 6-4 A, 6-4 B and 6-4 C (the final
fights). The list wraps around, so **Left** from 1-1 goes straight to
6-4 C. Press **Run** to start the chosen stage.

![STAGE 3-1 chosen](images/options/menu-stage.png)

### Parallax

With **PARALLAX** chosen, press **Left** or **Right** to choose:

- **ON**: this patch's smoother, slower parallax backgrounds (Enhanced, the
  default).
- **OFF**: the game's original backgrounds.

![PARALLAX OFF chosen](images/options/menu-parallax.png)

Enhanced parallax covers 1-1, 2-2, 3-1, 3-2, 4-1, 4-2, 5-2, 5-3, 5-4, 6-1
and 6-3. The other stages look the same with either setting. Enhanced
changes only the backgrounds: in emulator tests, Enhanced plays frame for
frame like the original game in all of these stages.

### No Damage

With **NO DMG** chosen, press **Left** or **Right** to choose **OFF** (the
default) or **ON**. With No Damage on, enemies and their attacks don't hurt
Ryu or knock him back. Falling into a pit or running out of time still costs
a life.

![NO DMG ON chosen](images/options/menu-no-damage.png)

Press **Run** to apply.

---

These screenshots were made in an emulator with
`scripts/guide_screenshots.py`; they show the original game's screens for
instruction. See the [README](../README.md) for patching and downloads.
