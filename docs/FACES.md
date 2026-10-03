# Clock Faces

Aurora Clock ships with **20 faces**. Every face is a pure render function, so
all of them automatically support every theme, the gradient engine, the
legibility effects (shadow / outline / glow / contrast plate) and the three
performance levels.

Change face in **Settings → Appearance → Clock face**.

![All faces](../preview_faces.png)

---

## Choosing a face

| I want… | Try |
|---|---|
| Something clean and readable | **Digital (classic)**, **Minimal** |
| Maximum size in a small window | **Stacked** |
| A retro look | **LED seven-segment**, **Flip cards** |
| A traditional clock | **Analog (numbers / minimal / roman)** |
| Something decorative | **Rings**, **Arc gauge**, **Neon tube**, **Dot matrix** |
| A thin strip along a screen edge | **Ticker strip** |
| Several time zones at once | **World clock** |
| Market hours | **Trader dashboard**, **Session timeline**, **Session board** |
| A talking point | **Word clock**, **Binary** |

---

## Reference

### Digital (classic) — `digital`

Big `HH:MM:SS` with AM/PM, date and label underneath. Automatically shrinks the
text to fit, and reflows depending on whether the date and label are shown.

*Best size:* wide — 400 × 150 and up.
*Cheapest option:* set Seconds to *Hidden* and it repaints about once a minute.

---

### LED seven-segment — `led`

Hexagonal seven-segment digits on an unlit-segment background, as on a real LED
display. Includes a correctly-shaped AM/PM indicator.

*Best size:* wide. Looks superb with the *Amber Glow*, *Matrix* or *Terminal
Green* themes, and a little glow.

---

### Analog (numbers) — `analog` · Analog (minimal) — `analog_minimal` · Analog (roman) — `analog_roman`

Three variants of a traditional dial:

| Variant | Dial markings |
|---|---|
| numbers | 1–12 in your chosen font |
| minimal | tick marks only |
| roman | I–XII |

The seconds hand sweeps smoothly or ticks depending on **Seconds**. Hands are
drawn through `draw_shape_fx`, so they pick up shadows, outlines and (if you
enable it) the gradient.

*Best size:* square. Use the **Square** size preset.
*Note:* a smooth seconds hand is the most expensive thing Aurora can draw — it
repaints at the animation rate. Use *Tick (1 s)* on battery.

---

### Flip cards — `flip`

Split-flap departure-board style cards for hours and minutes, with a hinge line
across each card.

*Best size:* wide, 420 × 180 and up.

---

### Rings / progress — `rings`

Three concentric progress rings — hours, minutes, seconds — with the time in
the middle. Each ring fills clockwise from the top.

*Best size:* square.

---

### Word clock — `text`

Spells the time out: *"quarter past nine"*, *"twenty-three minutes to five"*.
Handles o'clock, quarters and halves idiomatically.

*Best size:* wide, with room for two or three lines.

---

### Binary — `binary`

Binary-coded columns of dots for hours, minutes and seconds. Lit dots are the
accent colour, unlit dots are dimmed.

---

### Bars — `bars`

Horizontal bars whose length represents hours, minutes and seconds, with the
numeric value at the end of each bar.

---

### Trader dashboard ★ — `trader`

The flagship trading face: large local time, plus a panel of market sessions
showing open/closed state, a countdown to the next transition, and overlap
highlighting.

*Needs:* at least one market enabled in **Settings → Sessions**.
*Best size:* 600 × 300 and up.

---

### Session timeline (24 h) ★ — `session_timeline`

A horizontal 24-hour bar with every enabled session drawn as a coloured band,
and a marker showing "now". The fastest way to see at a glance which markets
overlap.

*Best size:* wide and short — ideal across the bottom of a monitor.

---

### Session board ★ — `session_board`

A compact table: market · status · countdown. Pure information, no decoration.

---

### World clock (multi-zone) — `world`

One row per time zone: city name, time, and UTC offset. Configure the zone list
in **Settings → Sessions / Time & Zone**.

*Best size:* tall and narrow.

---

### Stacked (hours over minutes) — `stack` 🆕 1.5

Hours on top, minutes below, each filling half the window — the largest
possible digits for a given area. Seconds sit small on the right, AM/PM small
on the left, and the date underneath.

*Best size:* square-ish or tall. **Readable from across a room.**

---

### Arc gauge — `arc_dial` 🆕 1.5

A 220° gauge sweeping through the 12-hour cycle, with a second inner arc for
minutes and the digital time in the centre.

*Best size:* wide, roughly 2:1.

---

### Neon tube — `neon` 🆕 1.5

Hollow outlined lettering with a multi-pass halo, like a bent glass neon sign.
The stroke uses the text colour (or your gradient) and the halo uses the
theme's glow colour.

*Best size:* wide.
*Best with:* *Neon Pink*, *Cyberpunk*, *Matrix*, *Bubblegum* themes, on a dark
wallpaper.

---

### Minimal (time only) — `minimal` 🆕 1.5

Just the time, in a light weight with wide letter spacing. No date, no label,
no AM/PM. The most understated face, and one of the cheapest to draw.

*Best size:* anything.

---

### Ticker strip (one line) — `ticker` 🆕 1.5

A single thin line: time on the left, label and date right-aligned. Designed to
be stretched across the top or bottom edge of a monitor at 40–60 px high.

*Best size:* very wide and short, e.g. 1200 × 48.

---

### Dot matrix — `dots` 🆕 1.5

Each unit of time is a column of twelve dots that light up in proportion to its
value, with the numeric value printed underneath.

*Best size:* square.

---

## Faces and the gradient engine

Every face draws through `draw_path_fx` (filled glyphs) or `draw_shape_fx`
(stroked shapes), so enabling **Settings → Appearance → Gradient colouring**
affects all of them. *Also colour hands, bars and rings* extends the gradient
from text to stroked shapes such as analog hands, rings and bars.

| Direction | Effect |
|---|---|
| Top to bottom | the classic metallic look |
| Bottom to top | inverted, good with *Fire* |
| Left to right | works beautifully with *Ticker strip* |
| Diagonal | the most dynamic |
| Centre outwards | a radial glow, excellent on *Rings* and *Arc gauge* |

---

## Performance notes

Aurora repaints only when the rendered content changes, so the cost of a face
depends on how often its appearance changes:

| Configuration | Repaints |
|---|---|
| Digital, seconds hidden | ~1 per minute |
| Digital, seconds ticking | 1 per second |
| Analog, smooth seconds hand | the full animation rate |
| Blinking colon | 2 per second |

**Settings → Application → Performance** scales the animation rate and the
number of shadow passes (1 / 3 / 4 for *Power saver* / *Balanced* / *Smooth*).

---

## Writing your own face

A face is a single function and about ten lines of boilerplate. The full guide,
including the `FaceContext` API and the helper functions, is in
[CONTRIBUTING.md § Writing a new clock face](../CONTRIBUTING.md#writing-a-new-clock-face).

New faces are the most welcome kind of pull request.
