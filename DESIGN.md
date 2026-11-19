---
name: "Lumen"
description: "Considered Capital — a cream-and-black paper-investing workspace."
colors:
  ink: "#292722"
  canvas: "#f7f4ec"
  surface: "#fffdf7"
  rail: "#211f1b"
  rail-text: "#f8f4e8"
  rail-active: "#403b32"
  secondary: "#ece6d9"
  muted: "#eee8dc"
  muted-text: "#71695d"
  detail-text: "#6c6457"
  border: "#e1dacb"
  input-border: "#cfc6b5"
  focus: "#877555"
  allocation-surface: "#eae2d2"
  allocation-1: "#3d3931"
  allocation-2: "#898474"
  allocation-3: "#c8baa0"
  allocation-4: "#b6aa92"
  allocation-5: "#a29c8f"
  cash: "#d5c9b2"
  positive: "#34684b"
  negative: "#a23f50"
typography:
  display:
    fontFamily: "Public Sans, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "2.75rem"
    fontWeight: 550
    lineHeight: 1.15
    letterSpacing: "-.035em"
  headline:
    fontFamily: "Public Sans, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-.035em"
  title:
    fontFamily: "Public Sans, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-.02em"
  body:
    fontFamily: "Public Sans, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: ".875rem"
    lineHeight: 1.5
  label:
    fontFamily: "Public Sans, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: ".75rem"
    fontWeight: 550
    lineHeight: 1.5
  button:
    fontFamily: "Public Sans, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: ".8125rem"
    fontWeight: 550
    lineHeight: 1.3
rounded:
  control: "7px"
  badge: "5px"
  surface: "13px"
  setup: "14px"
  avatar: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "18px"
  panel: "23px"
  lg: "24px"
  section: "28px"
  xl: "32px"
  page: "42px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "white"
    rounded: "{rounded.control}"
    padding: "10px 17px"
    typography: "{typography.button}"
  button-primary-hover:
    backgroundColor: "#484136"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "#514535"
    rounded: "{rounded.control}"
    padding: "10px 17px"
    typography: "{typography.button}"
  button-secondary-hover:
    backgroundColor: "#eae2d2"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px"
    typography: "{typography.button}"
  input:
    backgroundColor: "white"
    textColor: "#3e372c"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "43px"
  nav-link:
    textColor: "#d4cdbd"
    rounded: "{rounded.control}"
    padding: "12px 16px"
  nav-link-active:
    backgroundColor: "{colors.rail-active}"
    textColor: "white"
  paper-badge:
    backgroundColor: "#ebe7db"
    textColor: "#5d5a50"
    rounded: "{rounded.badge}"
    padding: "5px 9px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
  allocation:
    backgroundColor: "{colors.allocation-surface}"
    rounded: "{rounded.surface}"
    padding: "24px"
  status-filled:
    backgroundColor: "#e8eee1"
    textColor: "#4d6b50"
    padding: "4px 7px"
    rounded: "4px"
  tab:
    backgroundColor: "transparent"
    textColor: "{colors.detail-text}"
    padding: "7px 13px"
    rounded: "6px"
  tab-active:
    backgroundColor: "#e8e0cf"
    textColor: "#3e3526"
---

# Design System: Lumen

## Overview

**Creative North Star: "Considered Capital"**

Considered Capital makes practice investing feel measured, legible, and approachable. Warm cream grounds the workspace; near-black navigation and controls provide clear wayfinding. A precise sans serif and aligned numbers give balances and holdings room to be understood.

The interface is restrained rather than ornamental: broad work areas, lightly separated data, and warm neutral selections. The allocation band is its recurring signature, showing cash alongside holdings. Green and red communicate financial outcomes and status; the user’s cream-and-black instruction governs the identity.

**Key Characteristics:**
- Cream canvas, cream data surfaces, and a near-black navigation anchor.
- One Public Sans family, compact controls, and tabular financial numerals.
- Flat surfaces, quiet dividers, and a continuous neutral allocation band.

## Colors

Warm cream and black form the identity; sand, stone, and charcoal distinguish data without competing with it. Frontmatter values are normative.

### Primary
- **Ink** (`ink`): principal text and primary actions.
- **Rail Black** (`rail`): persistent desktop rail and mobile navigation; **Rail Text** supplies its light foreground, and **Rail Active** marks the current destination.

### Neutral
- **Warm Canvas** (`canvas`): the page background; **Cream Surface** (`surface`): holdings, chart, trade, setup, and account-popover surfaces.
- **Secondary / Muted**: quiet supporting surfaces; **Muted Text** is the semantic muted token, while **Detail Text** is the repeated small-text color in custom components.
- **Border / Input Border / Focus**: dividers, semantic input boundaries, and visible keyboard outlines. Custom form inputs use the closely related stroke recorded in their component snippet.
- **Allocation Surface**: the sand panel; **Allocation 1–5 / Cash**: warm neutral band segments and legend markers. These identify composition, not performance.

Green (`positive`) and red (`negative`) are functional outcome colors. Filled, pending, canceled, and error treatments also carry visible text, so their meaning does not depend on color alone.

**The Cream and Black Rule.** Use warm cream and near-black for identity; reserve green and red for financial outcomes and status.

## Typography

**Display Font:** Public Sans, with platform sans-serif fallbacks.
**Body Font:** Public Sans, with the same fallback stack.

The variable font is self-hosted with `next/font/local` from `frontend/public/fonts/PublicSans-Variable.ttf` (weights 100–900, `display: swap`; license beside it in `OFL.txt`). No separate display or monospace family is used in the rebuilt workspace.

### Hierarchy
- **Display:** portfolio equity; responsive sizes are described in Layout. Financial emphasis uses medium weight and tight tracking.
- **Headline:** page titles; compact mobile equivalent preserves the hierarchy.
- **Title:** section headings; table/card sections commonly use (1rem), and small subsection titles use (.9375rem).
- **Body:** application default; paragraph measure is capped at (72ch), with shorter component-specific measures.
- **Label:** form labels and supporting headings; controls use the separate button role. Supporting table labels and timestamps commonly use (.6875rem); selected compact mobile metadata uses (.5625rem).

**The Aligned Numbers Rule.** Use tabular numerals for balances, quantities, prices, and return columns; keep numeric table cells right-aligned.

## Layout

The desktop shell uses a fixed left rail (220px), matching main offset, a header (86px), and a centered main area capped at (1620px). Default main padding is (37px 42px 40px). Page headings pair a title/description with wrapping actions. The open summary uses three columns (1.25fr 1fr 1fr), divided by quiet rules rather than individual cards.

Portfolio work uses a flexible holdings column and an allocation aside (272px), separated by (28px). An empty portfolio omits allocation, recent activity, and return breakdowns until data exists. Research uses a flexible chart and a trade ticket (316px) with the same gap. Tables scroll within their container when needed; headers and numeric columns remain stable. Component padding and gaps draw from the extracted spacing vocabulary, with (8–12px) control gaps and (18–24px) interior padding.

- **At ≥1500px:** main top padding becomes (44px), portfolio aside (300px), gap (34px), table row vertical padding (22px), and equity (3rem).
- **At ≤1200px:** rail/offset become (192px), main/header horizontal padding (28px), portfolio aside (234px) with (20px) gap, research ticket (290px), and equity (2.375rem).
- **At ≤1020px:** portfolio and research become single-column; the allocation aside remains a single column. The trade ticket loses sticky positioning; setup becomes one column and the mobile trade jump action appears.
- **At ≤760px:** the rail disappears; four labeled destinations move to a fixed bottom bar (68px, with safe-area padding). Header height is (71px); main padding is (28px 21px 30px). Equity occupies its own summary row at (2.625rem), followed by two smaller balance columns. Page headings become (1.5rem); allocation and supporting content stack. Activity orders use readable cards rather than the desktop order table. Lower-priority table detail is adapted or hidden by the implemented mobile patterns.

## Elevation & Depth

Depth comes mainly from cream-on-cream tone, a dark navigation anchor, fine dividers, and spacing. Resting data panels have no shadow. Floating account menus, chart tooltips, the mobile bar, and the active buy/sell segment use restrained shadows.

### Shadow Vocabulary
- **Account menu:** `0 10px 36px #211f1b24`.
- **Chart tooltip:** `0 5px 22px #211f1b20`.
- **Mobile bar:** `0 -3px 15px #211f1b10`.
- **Selected side:** `0 2px 4px #211f1b0c`.

**The Flat Workspace Rule.** Separate resting work areas with tone and fine rules. Reserve visible shadows for floating information and small selected controls.

## Shapes

Controls and navigation have gently curved corners; larger work surfaces have broader rounding. Badges are smaller rounded rectangles, while account avatars and trade-state icons are circles. Asset identity uses locally cached company logos in (38px) frames with (11px) corners; mobile frames are (34px) with (10px) corners. White source logos use an ink backing. Missing logos fall back to the full ticker. The allocation band uses a compact (4px) outer radius and (3px) gaps between segments. Borders are thin, warm, and structural; company logo images identify investments and are never used as decorative imagery.

## Components

### Buttons
Confident, compact actions. Primary buttons use ink with white text, secondary buttons a transparent fill and warm outline, and quiet actions omit the outline. Standard actions have minimum height (41px), a (9px) icon gap, and the padding/radius recorded above. Hover darkens the primary or warms secondary/quiet fills. Disabled buttons use half opacity and a disabled cursor. Keep inline SVG icons beside readable labels where space permits.

### Inputs / Fields
Plain, clearly labeled fields use a white fill, warm border, and comfortable height. Custom fields are (43px) high with (12px) horizontal padding; labels sit (8px) above. Focus changes the border and preserves the shared keyboard outline (2px, offset 4px). Error notices use muted red text with a pale red surface and include an actionable message or retry.

### Navigation
The rail uses a modest icon and sentence-case label; current links have a warm dark fill and `aria-current="page"`. Hover uses a distinct darker neutral. On mobile, retain labels under the icons. Global search has a visible keyboard shortcut on desktop and a named icon button on mobile. Signed-in account choice and sign out live in a secondary popover. Login and signup use a compact, centered form.

### Chips / Tabs
The paper-trading badge is informational, not interactive. Filled, pending, and canceled chips spell out status. Range/filter buttons use a neutral active fill and stronger text, with `aria-pressed` when they function as toggles. Keep each role distinct from the primary action.

### Cards / Containers
Cream work surfaces use broad rounded corners and no resting shadow. Table section headers use (22px 23px) padding; chart panels and order tickets use approximately (23px). The sand allocation panel uses its own contrasting fill and (24px) padding. Setup forms use slightly rounder corners and (28px) padding on desktop.

### Allocation Band
A continuous, labeled cash/holdings composition is the signature pattern. The band is (24px) high with neutral segments; the legend repeats every segment color with aligned numeric percentages. Do not substitute a performance chart. Segment widths transition over (.35s) using `cubic-bezier(.16,1,.3,1)`.

### Data and Trade States
Tables use compact asset identities, secondary names, right-aligned values, row dividers, and a pale warm hover. Trade review visibly pairs estimated cash/share impact with a paper-order confirmation. Loading uses breathing skeletons (1.8s), refresh uses a spinning icon (1s), and ordinary button state transitions last (.18s ease-out). Under `prefers-reduced-motion: reduce`, animations and transitions are removed and scrolling is immediate. Price-history lines are linear and unanimated.

## Do's and Don'ts

### Do:
- **Do** keep paper-trading labels and meaningful market-data timestamps visible.
- **Do** preserve cash as part of the allocation band and align its legend values.
- **Do** stack work areas at the observed breakpoints and retain the four labeled mobile destinations.
- **Do** preserve focus outlines, loading/error/empty distinctions, and reduced-motion behavior.

### Don't:
- **Don’t** reintroduce the superseded plum-and-lilac palette.
- **Don’t** use gain/loss colors as decorative brand accents.
- **Don’t** invent portfolio-performance history or style locally remembered portfolios as secure sign-in.
- **Don’t** turn every balance into an isolated elevated card; retain the open summary hierarchy.

Instructional copy stays secondary: no sidebar slogans or automatic beginner checklist. Order explanations and OHLC data use closed-by-default disclosures. Quote times, trade totals, balances, validation, and order status remain visible.
