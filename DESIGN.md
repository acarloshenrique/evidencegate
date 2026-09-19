# DESIGN.md — EvidenceGate

Owner-supplied direction: Stripe-inspired financial-infrastructure tokens,
Apple-grade restraint (clean, luxurious, quiet), glass morphism used
functionally — never decoratively. Source of truth in code:
`app/web/eg.css`.

## World

Two tracks, one grammar:

- **Marketing track (light):** canvas white + canvas-soft, gradient mesh in
  the upper third of heroes (cream · sherbet · lavender · indigo · ruby —
  organic radial blobs, not a flat linear gradient), ink navy text, one
  filled indigo pill CTA per band.
- **Operate track (dark):** dashboards and consoles run on deep navy
  (`--d-bg #0a0e1e`) with ambient indigo/ruby/live glows and dark-glass
  panels. Same type, same tabular numerals, same pill geometry.

## Tokens

Defined as CSS custom properties in `app/web/eg.css` (`:root`). Palette,
spacing (2/4/8/12/16/24/32/64/96), radii (6/8/12/16/pill), elevation
(elev-1, elev-2, elev-glass), semantic colors for product surfaces only.

## Typography

- **Inter var** (self-hosted, `app/web/fonts/`) — open analogue of Söhne —
  at weight 300 for display and body; 400 for buttons/captions.
- `font-feature-settings: "ss01"` on body; `tnum` + tight tracking on any
  cell carrying money or counts (`.num`, `.caption`).
- Display scale 56/48/32/26 with negative tracking −0.04em → −0.02em;
  collapses 56→36 on mobile.
- Thin weight is the brand: never bump display above 300.

## Signature elements

- **Gradient mesh:** five blurred radial blobs (`.mesh`), faded into canvas;
  present on every marketing hero.
- **Glass:** `backdrop-filter: blur(20px) saturate(1.7)` — only where content
  scrolls beneath (fixed nav, floating live panel). Dark variant
  `glass-dark` for operate panels.
- **Wordmark:** authored shield-check SVG, 1.6px stroke, indigo on light /
  soft indigo on dark.
- **Pill buttons:** primary indigo fill; secondary = white + inset ring;
  dark = brand-dark-900. Padding 8–10 × 16–20.

## Hard rules (from craft floor + design.md)

- No kicker/eyebrow above headings — the heading carries its own weight.
- No gradient text — emphasis comes from weight/size.
- One filled CTA per band; indigo never as body text color.
- Card gets border or shadow, not both (no ghost card).
- Icons are drawn (inline SVG, consistent 1.5–1.6px stroke) — never emoji.
- No same-size icon-cards as page structure; editorial rows with hairlines
  carry feature lists.
- Tabular figures on every money/count cell.
- Section numbers only where the sequence itself is information
  (the escrow pipeline qualifies; decorative numbering does not).

## Detector

`./.agents/skills/impeccable/scripts/impeccable detect --json app/web/`
runs the mechanical anti-slop pass after UI edits.
