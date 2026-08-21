# Pathway Comparison — Features #3 & #6 (CaneCycle / BioOptima)

## Important context
No BioOptima source repository was ever shared in this conversation, despite
being asked for twice. Because of that, this could not be built as an edit to
your real files — that would have meant guessing at (i.e. inventing) files
that may not match your actual codebase. Instead, this is a **self-contained,
drop-in component**: three files, no new dependencies, designed to be pasted
into whatever page currently renders the cluster / recommendation drill-down.

When you're ready to wire it in for real, send the actual repo (or at least
the target page/component + `package.json`) and this can be integrated
directly, adjusted to match existing class names/theme tokens, and placed in
the exact right spot instead of being handed to you loose like this.

## What's in the zip
```
src/
  pathwayData.js        Dataset + calculation + optimizer engine (pure functions, no UI)
  PathwayComparison.jsx  The component (hero slider, table, toggle, quantity selector, details)
  PathwayComparison.css  Scoped styles (all classes prefixed `pc-`)
README.md               This file
index.html               Standalone, zero-build-step HTML/CSS/JS version (same design + logic)
```

## Dependencies
**None beyond React itself.** No charting library was added — the "Margin vs
Emissions" visual is plain CSS bars (see `.pc-scale` in the CSS), since a
five-row, two-metric comparison doesn't need a charting dependency. If your
app already has Recharts/Chart.js/etc. installed for other views, this can be
swapped to use it for visual consistency — just say the word.

## How quantity + calculations work
- `pathwayData.js` stores **per-tonne** rates only (revenue, transport cost,
  processing cost, emissions) for each of the 5 pathways.
- `calculateForQuantity(quantity)` is a pure function: it multiplies every
  rate by the selected quantity and derives `netMargin` and `co2Avoided`
  (baseline "Open Burning" emissions minus the pathway's emissions, floored
  at 0).
- The component re-runs this via `useMemo` whenever quantity changes (preset
  button or custom input), so all 5 rows recalculate together, always from
  the same quantity.
- "Highest margin" / "Lowest emissions" badges are computed dynamically each
  time, not hardcoded — they'll move if you change the underlying rates.

## Feature 06 — Objective-Weight Optimizer (the hero slider)
A slider lets the user balance **Maximum Margin ↔ Maximum Emissions Avoided**.
Moving it:
- Recomputes which pathway is "Recommended" using a weighted score.
- Updates the net margin and CO₂e avoided shown for that pick.
- Regenerates a short "why this pathway" explanation.
- Updates the live "Margin: X% | Emissions: Y%" readout.

This lives in three new pure functions in `pathwayData.js`, none of which
touch the component's markup logic:

- `scorePathways(rows, marginWeightPct)` — normalizes each candidate
  pathway's net margin and CO₂e avoided against the best-in-class value at
  the current quantity, blends them with the slider's weight, and returns
  every pathway sorted by score (baseline "Open Burning" excluded — it's
  never a candidate).
- `getOptimalPathway(rows, marginWeightPct)` — convenience wrapper that
  returns just the top-scored pathway.
- `explainRecommendation(pick, marginWeightPct)` — generates the short
  rationale text shown in the hero card and the why-box.

**Demo dataset note:** to make the slider meaningfully change the
recommendation (rather than always returning the same pathway regardless of
weighting), Biochar's `emissionsPerTonne` in the mock data is modeled as
slightly net-negative (-0.15), reflecting biochar's soil carbon-sequestration
credit — a standard assumption in biochar lifecycle-assessment literature.
This creates a genuine two-way trade-off: 2G Ethanol wins on margin, Biochar
wins on emissions avoided, and the other three pathways are dominated on both
axes so they never win regardless of weighting (this mirrors how a real
Pareto-frontier optimizer would behave). Replace with real LCA figures when
wiring up live data.

### Where to connect a real LP/optimizer backend
Keep `scorePathways`'s input/output shape (`rows` in, pathways sorted by
`.score` out) and swap its body for a fetch:

```js
export async function scorePathways(rows, marginWeightPct, clusterId) {
  const res = await fetch(`/api/clusters/${clusterId}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      marginWeight: marginWeightPct / 100,
      emissionsWeight: 1 - marginWeightPct / 100,
    }),
  });
  return res.json(); // pathways sorted desc by `score`, same fields
}
```
The component only ever reads `.score` / `.normMargin` / `.normEmissions`
off the returned list, so `PathwayComparison.jsx` would not need to change.

## Where to connect real backend/optimizer data (Feature 03 base dataset)
Everything real data needs to change lives in **`pathwayData.js` only** —
the component never touches raw numbers directly:

1. Replace the hardcoded `PATHWAYS` array with a fetch to your LP
   optimizer / recommendation endpoint, scoped to the active cluster:
   ```js
   export async function fetchPathwaysForCluster(clusterId) {
     const res = await fetch(`/api/clusters/${clusterId}/pathways`);
     return res.json(); // must match the PATHWAYS shape in this file
   }
   ```
2. The `isRecommended` static flag on `PATHWAYS` is no longer read by the
   UI — the "Recommended" badge now comes entirely from `getOptimalPathway`
   (Feature 06). You can leave the flag in your data as metadata or drop it.
3. Pass the resolved cluster's pathway list into `PathwayComparison` as a
   prop instead of the static import, e.g. `<PathwayComparison pathways={data} clusterName={cluster.name} />`
   (small change to the component's `useMemo` call to use the prop).
4. The five rate fields (`revenue`, `transportCost`, `processingCost`,
   `emissionsPerTonne`) are the only things that need to come from your
   backend — everything else (badges, sorting, bar widths, formatting,
   the optimizer score, the recommendation) is derived.

## Design notes
- Colors are CSS variables declared on `.pc-root` (`--pc-margin`,
  `--pc-emissions`, `--pc-warn`, etc.) — override them from a parent
  stylesheet to match BioOptima's real palette instead of editing the file.
- All classes are prefixed `pc-` to avoid collisions with existing site
  styles.
- Sticky first column + horizontal scroll on the table handles both desktop
  (full readable columns) and mobile (scrolls instead of breaking layout),
  per the brief — no separate mobile card variant was built, to keep one
  source of truth for the data instead of two markup paths.
- The Feature 06 hero card reuses the same `--pc-margin` / `--pc-emissions`
  tokens as the rest of the page (slider fill, glows, metric colors) so it
  reads as part of the same design system rather than a bolted-on widget.

