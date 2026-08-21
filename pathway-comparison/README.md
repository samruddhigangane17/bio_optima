# Pathway Comparison — Feature #3 (CaneCycle / BioOptima)

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
  pathwayData.js        Dataset + calculation engine (pure functions, no UI)
  PathwayComparison.jsx  The component (table, toggle, quantity selector, details)
  PathwayComparison.css  Scoped styles (all classes prefixed `pc-`)
README.md               This file
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

## Where to connect real backend/optimizer data
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
2. Set `isRecommended: true` on whichever pathway your optimizer returns as
   the Pareto-optimal pick for that cluster (currently hardcoded on the
   "2G Ethanol" entry).
3. Pass the resolved cluster's pathway list into `PathwayComparison` as a
   prop instead of the static import, e.g. `<PathwayComparison pathways={data} clusterName={cluster.name} />`
   (small change to the component's `useMemo` call to use the prop).
4. The five rate fields (`revenue`, `transportCost`, `processingCost`,
   `emissionsPerTonne`) and the two narrative fields (`whyRecommended`,
   `details.*`) are the only things that need to come from your backend —
   everything else (badges, sorting, bar widths, formatting) is derived.

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
