#!/usr/bin/env python3
"""Write captures/bg-fidelity/report/index.html from the analysis outputs."""
import html
import json
from pathlib import Path
import local

R = local.CAPTURES
REP = R / 'report'
compose = {f"{a['stage']}/a{a['subarea']}": a for a in json.loads((REP / 'compose.json').read_text())}
pairs = json.loads((REP / 'pairs.json').read_text())
integrity = json.loads((REP / 'integrity.json').read_text())
runs = {d.name: json.loads((d / 'run.json').read_text()) for d in sorted((R / 'orig').iterdir())
        if (d / 'run.json').exists()}

VERDICT = {
    '00-1-1': ('ok', 'Faithful', 'Native skyline art on a 256-px loop. 56 edited pixels (0.2%) in one row; '
               'loop joins land on building edges and read naturally. Opening view identical to the original.'),
    '03-2-2': ('note', 'Faithful art, recomposed (intentional)',
               'Native art on a 200-px loop: 56 native columns are dropped (the partial mountains at the screen '
               'edges), the left mountain\'s left slope is redrawn narrower (documented contour edit) and the '
               'cloud joins are hand-bridged. About 1% of loop pixels are edited. Area openings are shifted '
               '32-56 px relative to the original.'),
    '05-3-1': ('ok', 'Faithful', 'Every column is native art (0 edited pixels). The 256-px wrap in the clouds '
               'and distant mountains reads as continuous. Opening view identical.'),
    '06-3-2': ('ok', 'Faithful (exact)', '0 edited pixels and no non-native joins detected. Opening view identical.'),
    '08-4-1': ('ok', 'Faithful', '0 edited pixels, no joins detected. Areas 2-3 are untouched (pixel-identical tile maps).'),
    '09-4-2': ('note', 'Faithful with documented cloud extension',
               'Sky clouds use the documented cloud-join extension across the 256-px loop; the distant '
               'mountain band is unedited native art. At the very first cave mouth (camera 0) the clouds '
               'framed in the opening differ from the original\'s.'),
    '13-5-2': ('bad', 'Defect: vista missing in areas 2 and 4',
               'Areas 1 and 3 (zero-based 0 and 2) match. In the second and fourth climbing screens the '
               'right-hand opening shows flat blue where the original shows clouds, a mountain and forest. '
               'Reproduced in a fresh, untouched emulator session.'),
    '14-5-3': ('warn', 'Mostly faithful; horizon wrap seam',
               'Castle-window sky and horizon are native art, but the horizon\'s 256-px wrap is unrepaired: a '
               'cloud is cut into a rectangular block with a straight vertical edge (seen in areas 4 and 6, '
               'zero-based 3 and 5). 6-1 has the documented repair for the same artwork. Area 5 (zero-based 4) '
               'opens 128 px shifted. Animated wall/chain tiles differ only by animation phase.'),
    '15-5-4': ('ok', 'Identical', 'Static boss arena: backdrop columns are identical to the original (0 edits).'),
    '16-6-1': ('note', 'Faithful with requested changes',
               'Upper sky and moon are stationary by design and sit within the original\'s 8-px jitter; '
               'the horizon scrolls at 1/8 speed with the documented cloud-join repairs at its wrap.'),
    '18-6-3': ('warn', 'Mostly faithful; arcade wrap seam',
               'Arcade backdrop is native art, but the 256-px wrap is not a multiple of the arch spacing: one '
               'arch is cut short by an extra pillar (areas 1 and 3, zero-based 0 and 2), usually beside the '
               'blue foreground column. Area 3 (zero-based 2) opens 80 px shifted.'),
}
LABEL = {'ok': 'Faithful', 'note': 'Intentional changes', 'warn': 'Seam found', 'bad': 'Defect'}

DEC_ORDER = [('control', 'Identical control (3-2 vs itself)', 'same'),
             ('clean-32', '3-2 clean pair (parallax-shifted clouds)', 'same'),
             ('repeat-22', '2-2 intentional 200-px recomposition', 'same'),
             ('vista-52', '5-2 missing vista (defect)', 'different'),
             ('seam-53', '5-3 horizon cloud block (seam)', 'different'),
             ('seam-63', '6-3 cut arch (seam)', 'different')]


def esc(s):
    return html.escape(str(s))


def stage_table():
    rows = []
    for st, (cls, title, _) in VERDICT.items():
        run = runs[st]
        n = len(run['samples'])
        areas = len(run['areas'])
        rows.append(f'<tr><td><b>{esc(run["stage_name"])}</b></td><td>{areas}</td><td>{n}</td>'
                    f'<td><span class="pill {cls}">{LABEL[cls]}</span></td><td>{esc(title)}</td></tr>')
    return '\n'.join(rows)


def decisions_table():
    out = []
    for name, label, expected in DEC_ORDER:
        p = R / 'decisions' / f'{name}.json'
        r = json.loads(p.read_text())
        a = {x['name']: x for x in r['response']['answers']}
        c = a['background_layers_same']
        ok = (c['choice'] == expected)
        out.append(f'<tr><td>{esc(label)}</td><td>{esc(expected)}</td><td>{esc(c["choice"])} '
                   f'({c["confidence"]:.2f})</td><td>{a["background_scenery_layer_missing"]["probability"]:.2f}</td>'
                   f'<td>{"✓" if ok else "missed"}</td><td><code>{esc(r.get("request_id"))}</code></td></tr>')
    return '\n'.join(out)


def stage_sections():
    out = []
    for st, (cls, title, text) in VERDICT.items():
        run = runs[st]
        name = run['stage_name']
        integ = integrity.get(st, {}).get('categories', {})
        areas = []
        for a in run['areas']:
            key = f'{st}/a{a["subarea"]}'
            c = compose.get(key, {})
            if c.get('identical'):
                areas.append(f'<li>Area {a["subarea"] + 1}: no background tile changes (identical to the original).</li>')
                continue
            rows = c.get('rows', {})
            ed = sum(v['edited_pixels'] for v in rows.values())
            img = c.get('image')
            areas.append(f'<li>Area {a["subarea"] + 1}: camera {a["camera_entry"]} at entry, '
                         f'{len(rows)} backdrop rows changed, {ed} pixels not reproducible from native art'
                         + (f' — <a href="{esc(img)}">panorama</a>' if img else '') + '</li>')
        pano = [f'<figure><img class="px" loading="lazy" src="{esc(compose[k]["image"])}" alt="">'
                f'<figcaption>Area {k.split("/a")[1] and int(k.split("/a")[1]) + 1}: native backdrop (top, '
                f'screen-locked) vs Enhanced texture (bottom, scrolls at 1/8). Magenta = columns not found '
                f'in native art; checkerboard = never visible.</figcaption></figure>'
                for k in compose if k.startswith(st + '/') and compose[k].get('image')]
        grid = ''.join(
            f'<figure class="pair"><img class="px" loading="lazy" src="{esc(p["file"])}" alt="">'
            f'<figcaption>Area {p["area"] + 1} · camera {p["camera"]} · {esc(p["kind"])}</figcaption></figure>'
            for p in pairs.get(st, []))
        out.append(f'''
<section id="s{esc(name)}">
  <h2>{esc(name)} <span class="pill {cls}">{LABEL[cls]}</span></h2>
  <p class="lead">{esc(text)}</p>
  <ul class="areas">{''.join(areas)}</ul>
  <p class="small">Screenshot integrity outside patched background cells: {esc(integ)}</p>
  <details><summary>Stitched backdrops ({len(pano)})</summary>{''.join(pano)}</details>
  <details open><summary>Matched snapshots: original (left) | Enhanced (right) — {len(pairs.get(st, []))} positions</summary>
    <div class="grid">{grid}</div></details>
</section>''')
    return '\n'.join(out)


page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Background Fidelity Review</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1f; --muted:#5f6368; --card:#ffffff; --line:#e3e1dc;
  --ok:#1e7a46; --note:#2f5fb3; --warn:#a86400; --bad:#b3261e; --code:#f1efea; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141416; --fg:#ececec;
  --muted:#a1a1a6; --card:#1d1d20; --line:#333338; --ok:#5cc98a; --note:#86a8ef; --warn:#f0b35a;
  --bad:#ff8a80; --code:#26262a; }} }}
:root[data-theme="dark"] {{ --bg:#141416; --fg:#ececec; --muted:#a1a1a6; --card:#1d1d20; --line:#333338;
  --ok:#5cc98a; --note:#86a8ef; --warn:#f0b35a; --bad:#ff8a80; --code:#26262a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:28px; margin:0 0 4px; }} h2 {{ margin-top:40px; border-top:1px solid var(--line); padding-top:24px; }}
.lead {{ font-size:16px; }} .small,.muted {{ color:var(--muted); font-size:13px; }}
table {{ border-collapse:collapse; width:100%; background:var(--card); }}
td,th {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
.pill {{ display:inline-block; border-radius:999px; padding:1px 10px; font-size:12px; font-weight:600;
  border:1px solid currentColor; vertical-align:middle; }}
.ok {{ color:var(--ok); }} .note {{ color:var(--note); }} .warn {{ color:var(--warn); }} .bad {{ color:var(--bad); }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; margin:16px 0; }}
img.px {{ image-rendering:pixelated; max-width:100%; height:auto; display:block; }}
figure {{ margin:10px 0; }} figcaption {{ color:var(--muted); font-size:12px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(500px,1fr)); gap:12px; }}
@media (max-width:560px) {{ .grid {{ grid-template-columns:1fr; }} }}
code {{ background:var(--code); padding:1px 4px; border-radius:4px; font-size:12px; }}
details summary {{ cursor:pointer; font-weight:600; margin:8px 0; }}
.scroll {{ overflow-x:auto; }}
</style></head><body><main>
<h1>Background fidelity review</h1>
<p class="muted">Ninja Ryukenden (J) raw ROM (SHA-256 1b3f411d…) vs Enhanced v1.01 (0ad5e8a5…), all 11 parallax stages,
emulated in headless Geargrafx. Generated 2026-10-11.</p>

<div class="card">
<h3 style="margin-top:0">Verdict</h3>
<p>In 8 of 11 stages the Enhanced backdrop is the original's own artwork. Nearly every pixel column
traces to a column of the native background. The only edits are small documented ones (2-2 contour and cloud
joins, 4-2 and 6-1 cloud joins). Every patched row follows the 1/8-camera scroll exactly, and the foreground, HUD,
palettes in use and sprites are untouched.
Three real problems turned up:</p>
<ol>
<li><b class="bad">5-2, second and fourth climbing screens:</b> the small vista at the right-hand opening is flat blue
instead of the original's clouds, mountain and forest. It reproduces in an untouched emulator session.</li>
<li><b class="warn">5-3 castle windows:</b> the horizon's 256-px wrap is unrepaired, so a cloud is cut into a block
with a straight vertical edge. 6-1 already has the repair for the same artwork.</li>
<li><b class="warn">6-3 arcade:</b> the 256-px wrap cuts one arch short with an extra pillar. It's mostly beside the
foreground column.</li>
</ol>
<p>Separately, area openings entered away from camera 0 are horizontally shifted relative to the original (2-2,
5-3 area 5, 6-3 area 3). That follows from the entrance-anchor formula, which reproduces the earlier half-speed
build's opening, not the original's screen-locked backdrop.</p>
</div>

<div class="card">
<h3 style="margin-top:0">Update: fixes prototyped in 1.02-dev</h3>
<p>The development build <code>build/dev/Ninja Ryukenden - Enhanced v1.02-dev.pce</code> (SHA-256
<code>7f347af3…4045</code>, branch <code>bg-fidelity-fixes</code>, not yet hardware-tested) fixes all
three problems and the 2-2 ridge tear:</p>
<ul>
<li><b>5-2:</b> a fixed anchor keeps the vista art in the opening in every climbing screen.</li>
<li><b>6-3:</b> the arcade loops every 240px (six arches), so no arch is cut.</li>
<li><b>5-3:</b> the castle horizon uses 6-1's already-repaired horizon at the seam. The static 5-4 arena
keeps its exact original view.</li>
<li><b>2-2:</b> the far ridge now repeats with the mountains, so the ridge no longer tears.</li>
</ul>
<p>Every untouched stage (1-1, 3-1, 3-2, 4-1, 4-2, 5-4, 6-1) is screenshot-identical to v1.01 in every
sample.</p>
<div class="grid">
<figure><img class="px" src="dev/fix52.png" alt=""><figcaption>5-2 area 2, camera 508: original | v1.01 | 1.02-dev</figcaption></figure>
<figure><img class="px" src="dev/fix63.png" alt=""><figcaption>6-3 area 1, camera 416: original | v1.01 | 1.02-dev</figcaption></figure>
<figure><img class="px" src="dev/fix53.png" alt=""><figcaption>5-3 area 4, camera 508: original | v1.01 | 1.02-dev</figcaption></figure>
</div>
</div>

<div class="card">
<h3 style="margin-top:0">Understanding 2-2</h3>
<p>The original 2-2 backdrop is a single 34-tile (272px) map that never scrolls; columns 32-33 only cover
the 8px jitter. Its cloud and mountain rows were drawn as a repeat: columns 32-33 equal 7-8 and, in rows
6-11 and 13, columns 25-26 equal 0-1. So the 200px loop is the original artists' own period, not an
invention. The frozen patch data only holds native columns 7-31 for those rows, which fixed the loop
window.</p>
<p>The creative judgement went into four places:</p>
<ol>
<li>The far ridge's upper rows (4-5) were left on a 256px loop while its lower rows used 200px, so the
ridge tore horizontally across about a third of the loop. This is now fixed.</li>
<li>Mountain A's left slope was reshaped to imitate mountain B's irregular outline.</li>
<li>A cloud tile join that exists in the original at x=128 was bridged with recoloured pixels.</li>
<li>One native tile was swapped at row 8 / column 31 so the loop join continues the cloud. This one is
required.</li>
</ol>
<p>"Could we do better?" Yes, in two steps: fix the ridge (done in 1.02-dev), and optionally drop edits 2
and 3 to show the original's own pixels. That optional build, <code>v1.02-dev (2-2 native
pixels)</code>, is 98.7% exact native windows with no non-native joins. Whether the original slope and
cloud join look better than the edits is a call only you can make, so it's a separate ROM.</p>
<figure><img class="px" src="dev/22-native-map.png" alt=""><figcaption>The original 2-2 backdrop map,
all 34 columns (2×)</figcaption></figure>
<figure><img class="px" src="dev/22-candidates.png" alt=""><figcaption>Two loops of each texture: v1.01
(ridge rows on 256px) | ridge fixed (edits kept, 1.02-dev) | ridge fixed + native pixels</figcaption></figure>
<figure><img class="px" src="dev/22-candidates-zoom.png" alt=""><figcaption>Zoom, top to bottom in the same
order. Left: the loop join at mountain A's left foot (the row-4 haze bump is the one remaining ridge-row
mismatch). Right: the x=128 cloud join.</figcaption></figure>
<figure><img class="px" src="dev/22-ridge-tear.png" alt=""><figcaption>v1.01 ridge (bottom) vs original
(top) in a real frame</figcaption></figure>
<figure><video src="dev/stage22-comparison.mp4" controls loop muted playsinline style="max-width:100%"></video>
<figcaption>2-2 area 3, full sweep, identical camera in all four: original | v1.01 | ridge fixed | ridge
fixed + native pixels</figcaption></figure>
</div>

<div class="card scroll"><table><tr><th>Stage</th><th>Areas</th><th>Matched samples</th><th>Result</th><th>Summary</th></tr>
{stage_table()}</table></div>

<h2>Defects</h2>
<h3 class="bad">5-2 — vista missing (areas 2 and 4)</h3>
<p>The original backdrop never moves (it is screen-locked, apart from an 8-px jitter), and in 5-2 it only has art
inside the narrow opening. Enhanced scrolls the texture at floor(camera/8)+anchor, and the anchor depends on the entry
camera. Areas 1 and 3 are entered at camera 512 and show the art where it belongs. Areas 2 and 4 are entered at
camera 0, so by the time the opening is on screen (camera 508) the texture has moved 63 px past the art and only
blank sky is left.
Fix options: derive this stage's anchor from the opening's position (or the area's far end), or render 5-2's areas
2 and 4 (or the whole stage) in Original mode.</p>
<figure><img class="px" src="defects/52-vista-untouched.png" alt=""><figcaption>Fresh emulator session, unmodified ROM,
no breakpoints or writes, 240 frames after reaching camera 508: original (left) vs Enhanced (right).</figcaption></figure>
<figure><img class="px" src="defects/52-vista-crops.png" alt=""><figcaption>The opening in four sweep samples
(areas 2 and 4), each as an original | Enhanced pair.</figcaption></figure>

<h3 class="warn">5-3 — horizon wrap seam in castle windows</h3>
<figure><img class="px" src="defects/53-cloud-block.png" alt=""><figcaption>Area 4, camera 508: original (left) vs
Enhanced (right). The Enhanced cloud ends in a straight vertical edge at the 256-px wrap (red tick).</figcaption></figure>
<figure><img class="px" src="defects/53-horizon-seams-texture.png" alt=""><figcaption>Enhanced texture around the
detected joins (4×). 6-1's equivalent horizon has the documented "textured flank" repair.</figcaption></figure>

<h3 class="warn">6-3 — arcade wrap seam</h3>
<figure><img class="px" src="defects/63-arch-seam.png" alt=""><figcaption>Area 1, camera 416: original (left) vs
Enhanced (right); the red tick marks the join, where an arch is cut short by an extra pillar.</figcaption></figure>
<figure><img class="px" src="defects/63-arch-seam-texture.png" alt=""><figcaption>Enhanced arcade texture at the
join (areas 1 and 3, 4×).</figcaption></figure>

<h3 class="note">2-2 — intentional recomposition, for reference</h3>
<figure><img class="px" src="defects/22-native-vs-enhanced-zoom.png" alt=""><figcaption>Native backdrop (top, one
fixed 256-px picture) vs the Enhanced 200-px loop (bottom). The mountains sit closer together and the left
mountain is narrower.</figcaption></figure>
<figure><img class="px" src="defects/22-repaired-joins.png" alt=""><figcaption>Hand-repaired cloud and contour
joins (4×). They read naturally.</figcaption></figure>

<h2>Independent check: Decisions API</h2>
<p>Six screenshot-pair calls (model gpt-6-luna, background focus, logged in the sugar-gliders usage journal). The API
confirms the large 5-2 defect and accepts the clean and intentional pairs. It does not catch the two small wrap
seams, so it is no substitute for the deterministic checks.</p>
<div class="card scroll"><table><tr><th>Pair</th><th>Expected</th><th>Background layers</th><th>P(missing scenery)</th>
<th></th><th>Request</th></tr>{decisions_table()}</table></div>

<h2>Stage by stage</h2>
{stage_sections()}

<h2>Method and limits</h2>
<ul>
<li><b>Emulation:</b> headless Geargrafx 78fc3d7 with the project's headless-fast patch (from sugar-gliders
<code>.local/toolchains</code>). This is emulator evidence, not hardware.</li>
<li><b>Same state on both ROMs:</b> both cold boot to the first gameplay update. Stages are entered by debugger writes
that mirror Level Select at <code>$83F3</code> (<code>$2241</code>, <code>$2247</code>, <code>$2248</code>,
progress cleared, then native <code>$8244</code>). Areas advance through the native forward transition
<code>$8490</code>.</li>
<li><b>Camera sweep:</b> at each gameplay update (<code>$8457</code>) the native scroll routine <code>$E341</code> is
called with <code>$220E</code> = ±4. Ryu is held at camera+128 at height <code>$60</code> with full health. Both
ROMs get the same NOP of the player-driven scroll call at <code>$925E</code> in the emulator's ROM buffer only.
Samples are taken every 32 camera px in both directions, plus each area entry: 1,734 matched pairs, with identical
camera and render camera in every pair. The 5-2 defect was re-checked without any of these interventions.</li>
<li><b>Background-only decoding:</b> the background layer is decoded from VRAM, the tile map and VCE palettes, so
sprites never contaminate it. Screen y = map row × 8 + 50, and screen x = map x − render camera, verified against
screenshots. Patched cells are those whose tile number differs between the ROMs at the same camera.</li>
<li><b>Motion models</b> (verified per row): Enhanced matches floor(camera/8) with 100% agreement (6-1 sky:
stationary). The native backdrop is screen-locked with an 8-px jitter that depends on travel history.</li>
<li><b>Provenance:</b> every 8-px Enhanced texture window was searched for in the same native row. Columns with no
match are counted as edited, and their pixel differences are measured against the neighbouring alignment.</li>
<li><b>Seams:</b> places where adjacent Enhanced columns never sit side by side in native art in two or more rows.
These were reviewed by eye. Wrap joins in 1-1, 3-1, 4-2 and 6-1 read naturally.</li>
<li><b>Missing scenery:</b> colour-histogram distance between the visible patched backdrops. High scores were
reviewed. Only 5-2 is a real defect; the others are narrow windows.</li>
<li><b>Not covered:</b> respawn or checkpoint entry cameras (these change the Enhanced alignment and could reveal other
loop regions), vertically scrolling sections, real-input crowded play, timing and performance, and the Original
mode setting. Sprite and animation-phase differences are present because the Enhanced splash offsets the frame
counters of the two runs; none affect the background.</li>
</ul>
<p class="small">Evidence: <code>captures/bg-fidelity/</code> (orig/enh samples with VRAM, RAM, palettes and SAT; analysis/;
report/*.json; decisions/; verify-5-2/; tools/).</p>
</main></body></html>'''
(REP / 'index.html').write_text(page)
print('wrote', REP / 'index.html', len(page))
