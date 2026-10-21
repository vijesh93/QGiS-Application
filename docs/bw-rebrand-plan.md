# Baden-Württemberg Branding & Legal Compliance Plan — Frontend

## Context

This app (the LAZBW climate-projections geoportal, currently deployed at
`https://klima-projektionen.ffs-apps.de`) is moving from an internal/trial
look toward a real production release. As a Baden-Württemberg state
(LAZBW) web application, it is expected to follow the state's corporate
design (design.landbw.de) and is legally required — under the
Landes-Behindertengleichstellungsgesetz (L-BGG) and the Telemediengesetz/
Medienstaatsvertrag — to be accessible (BITV 2.0) and to publish an
Impressum, a Datenschutzerklärung, and an Erklärung zur Barrierefreiheit.
None of this exists today; the frontend currently has no branding, no
legal pages, and an incomplete HTML document shell. This plan closes
those gaps so the app is presentable and compliant for a public launch.

## Research summary

### Corporate design (design.landbw.de)

The state's digital design portal (design.landbw.de) requires a login for
asset downloads (logo files, licensed fonts), but its public pages define
the full color and typography system:

**Primary colors (mandatory):**
| Name | Hex |
|---|---|
| BaWü Gelb | `#FFFC00` |
| BaWü Schwarz | `#2A2623` |
| Weiß | `#FFFFFF` |

**Grayscale:**
| Name | Hex |
|---|---|
| Grau 1 | `#F4F3F3` |
| Grau 2 | `#E4E0E0` |
| Grau 3 | `#BBB6B5` |
| Grau 4 | `#918C8C` |
| Grau 5 | `#6D6766` |
| Grau 6 | `#47403C` |

**Secondary colors** (supplementary only — infographics etc.):
Lila Hell `#C761EC` / Lila Dunkel `#6B108C`, Türkis Hell `#309AAF` /
Türkis Dunkel `#094954`, Orange Hell `#DD6F06` / Orange Dunkel `#6A3201`.

**Functional colors** (digital-only, fixed semantic meaning — do not
repurpose): Info/Blau Hell `#508CF1` / Dunkel `#0A3C90`; Erfolg/Grün Hell
`#609D0F` / Dunkel `#2B4904`; Fehler/Rot Hell `#FD4D4D` / Dunkel `#85100C`.

**Typography:** two custom licensed typefaces — **BaWue Serif** (headlines)
and **BaWue Sans** (body text), explicitly designed for contrast and
barrier-free readability. As of July 2026 the font license was expanded to
cover app use, not just web/print. You have portal access, so you'll pull
the actual font files and the official logo SVGs yourself; this plan
treats them as drop-in assets with documented placeholder paths until then.

### Legal / accessibility requirements

- Legal basis: **§10 Abs. 1 L-BGG** (Landes-Behindertengleichstellungsgesetz),
  which points to **BITV 2.0**, which in turn adopts **EN 301 549 v3.2.1**
  (which incorporates **WCAG 2.1**) as the technical standard.
- Required publications: an **Erklärung zur Barrierefreiheit**
  (accessibility statement) containing: compliance status, a list of
  known non-accessible content with explanation, the statement's
  creation/review date, a feedback contact for reporting barriers, and a
  reference to the dispute-resolution body (Landeszentrum Barrierefreiheit
  / Schlichtungsstelle) if the responsible office doesn't resolve a report
  within 4 weeks.
- Standard BW-site footer pattern (confirmed across multiple ministry
  sites): **Impressum**, **Datenschutz**, **Erklärung zur
  Barrierefreiheit**, often also **Benutzungshinweise**.
- Impressum content is governed separately by media law (§5 TMG /
  §18 Medienstaatsvertrag): operator name and address, a
  Vertretungsberechtigte(r), contact (phone/email), and the person
  redaktionell verantwortlich if the site has editorial content.

## Current frontend state (gaps found)

A codebase exploration found:
- `frontend/index.html` has no `<!DOCTYPE html>`, no `<head>`, no
  `<title>`, no meta tags, no favicon — just a bare `<div id="root">`.
- No design tokens anywhere — Tailwind v4 is used with zero customization
  (no `@theme` block), plus hardcoded hex colors scattered inline
  (`#1f3a52` scrollbar, Material-ish category colors
  `#4FC3F7, #81C784, #FFB74D, ...` duplicated in both
  `Sidebar.jsx` and `ActiveLayersLegend.jsx`).
- No header/logo component — the only branding is a plain-text "BW
  Geoportal" label in `Sidebar.jsx:80` and a text-only footer line
  (`Sidebar.jsx:242-246`).
- No Impressum, Datenschutz, or accessibility-statement pages/routes exist
  at all.
- No router (no `react-router-dom` or equivalent) — `App.jsx` is a flat
  layout with just `Sidebar` + `MapView` + `ActiveLayersLegend`.
- Base map is raw OpenStreetMap raster tiles via MapLibre GL, with
  hardcoded attribution — functionally fine and correctly attributed, not
  a compliance blocker.
- No component library; styling is Tailwind utility classes plus raw
  inline `style={{}}` objects.

## Proposed changes

### 1. Document shell (`frontend/index.html`)
Rewrite with a proper `<!DOCTYPE html>`, `<html lang="de">`, `<head>`
containing charset, viewport, a real `<title>`, meta description, and a
favicon link. `lang="de"` is also an accessibility requirement (screen
readers need the page language declared).

### 2. Design tokens (`frontend/src/styles/index.css`)
Tailwind v4 uses CSS-first config via an `@theme` block (no
`tailwind.config.js` needed). Define the BW palette there as Tailwind
theme colors / CSS custom properties — primary (Gelb/Schwarz), grayscale
(Grau 1–6), secondary, and functional colors — so `bg-bawu-gelb` etc.
become available utility classes, replacing today's ad-hoc dark
slate/blue theme for UI chrome. Add `@font-face` rules for BaWue Serif
(headings) / BaWue Sans (body) once the licensed files are in hand, with
a sensible system-font fallback stack in the meantime so nothing blocks
on asset delivery.

### 3. Header / branding component
New `frontend/src/components/Header.jsx`: logo (placeholder path
`frontend/public/logo-bw.svg` until the real asset is dropped in) + app
title, styled with the new BW tokens. Mounted above the existing
Sidebar/MapView layout in `App.jsx`.

### 4. Footer + legal pages
- Add `react-router-dom` (new dependency) for real, linkable, printable
  routes: `/`, `/impressum`, `/datenschutz`, `/barrierefreiheit`.
- New `frontend/src/components/Footer.jsx` with links to the three legal
  pages (replacing/extending the current text-only footer line in
  `Sidebar.jsx`).
- New pages under `frontend/src/pages/`:
  - `Impressum.jsx` — LAZBW as the responsible entity (confirmed), with
    placeholder fields for exact address/Vertretungsberechtigte/contact
    (see Open Items).
  - `Datenschutz.jsx` — placeholder DSB contact + a description of what
    data this app actually processes (needs confirming — see Open Items).
  - `Barrierefreiheit.jsx` — accessibility statement per §10 L-BGG:
    compliance status, known barriers, creation/review date, feedback
    contact, and the Landeszentrum Barrierefreiheit mediation reference.

### 5. Accessibility implementation (BITV 2.0 / WCAG 2.1 AA)
- `lang="de"` on `<html>` (item 1) and a skip-to-content link.
- Verify color contrast for every text/background pairing against WCAG AA
  (4.5:1 normal text, 3:1 large text/UI components) — BW's Gelb/Schwarz
  pairing is naturally high-contrast, but grayscale-on-white combinations
  need checking individually.
- Keyboard navigation through the sidebar and map controls (MapLibre's
  `NavigationControl` is keyboard-accessible by default — verify after
  restyling).
- `aria-label`s on icon-only buttons (the app uses `lucide-react` icons
  throughout).
- Visible focus outlines (confirm Tailwind defaults aren't suppressed
  anywhere).
- Plain, clear German in all new legal/help text.

### 6. Data-layer category colors (kept separate from brand chrome)
The current Material-style palette differentiates map *layer categories*
in the sidebar/legend — that's a data-visualization concern, not brand
chrome, and BW's corporate design doesn't mandate a specific data-viz
palette. Recommendation: keep a distinct categorical palette for layers,
contrast-checked for accessibility, while UI chrome (header, footer,
buttons, links, backgrounds) follows the BW Gelb/Schwarz identity.
Conveniently, BW's own secondary palette (Lila/Türkis/Orange × hell/dunkel
= 6 distinct, pre-approved hues) is a reasonable source for this if a BW-
consistent look is wanted there too — worth a quick call but not a
blocker.

### 7. Base map / attribution
No change required for compliance — OSM tiles with correct attribution
are fine as-is. Optional future enhancement (not part of this pass):
swap to an LGL-BW (Landesamt für Geoinformation und Landentwicklung BW)
basemap for a more "official" cartographic look.

## Files to create/change (representative)

- `frontend/index.html` — rewritten head
- `frontend/src/styles/index.css` — `@theme` tokens + `@font-face`
- `frontend/src/components/Header.jsx` — new
- `frontend/src/components/Footer.jsx` — new
- `frontend/src/pages/Impressum.jsx`, `Datenschutz.jsx`,
  `Barrierefreiheit.jsx` — new
- `frontend/src/App.jsx` — wire in router, Header, Footer
- `frontend/package.json` — add `react-router-dom`
- `frontend/public/` — new directory for logo/favicon (placeholders
  initially, real assets dropped in later)
- `frontend/src/components/Sidebar.jsx`, `ActiveLayersLegend.jsx` —
  restyle chrome onto BW tokens; category palette per item 6

## Open items — need your input before/during implementation

1. **Logo + fonts**: you'll pull the official logo SVG(s) and BaWue
   Serif/Sans font files via your design.landbw.de login. I'll document
   exact expected filenames/paths when implementation starts.
2. **Impressum details**: LAZBW's postal address, Vertretungsberechtigte
   (e.g. Direktor/in), phone, email, Aufsichtsbehörde (if applicable), and
   the redaktionell verantwortliche Person (§18 Abs. 2 MStV).
3. **Datenschutzbeauftragter (DSB)**: name/role or department contact for
   LAZBW's data protection officer, to list in the Datenschutzerklärung.
4. **Data processing confirmation**: does this app set cookies or use any
   analytics/tracking? Code review found none so far, but this needs
   confirming — it affects whether a cookie-consent banner is additionally
   required under TTDSG.
5. ~~**App title**~~ — resolved: **KlimaWandeln**. Set in
   `frontend/src/constants/brand.js` (`APP_TITLE`), used in `index.html`'s
   `<title>`, the `Header`, and the sidebar header/footer.

## Verification plan

- `npm run dev` in `frontend/`: header/footer render correctly, all three
  legal pages are reachable and print cleanly.
- Accessibility: run an axe/Lighthouse accessibility audit (target: no
  critical issues) and manually tab through the whole UI to confirm
  keyboard operability.
- Contrast: check every new text/background pairing against WCAG AA with
  a contrast checker.
- `npm run build` succeeds and includes the new routes.
- After deploying: rebuild the `gateway` image on the server
  (`docker-compose.prod.yml`) and confirm
  `https://klima-projektionen.ffs-apps.de/impressum` (etc.) resolve
  correctly in production.
- Have someone at LAZBW sanity-check the exact legal wording in
  Impressum/Datenschutz/Barrierefreiheit before the app is fully public —
  I can draft correct structure and boilerplate, but the organization
  should confirm factual/legal accuracy of the final text.
