import React, { useMemo, useState } from "react";
import {
  PATHWAYS,
  QUANTITY_PRESETS,
  calculateForQuantity,
  formatCurrency,
  formatTonnes,
} from "./pathwayData";
import "./PathwayComparison.css";

/**
 * <PathwayComparison />
 * ---------------------------------------------------------------------------
 * Feature #3 — Pathway Comparison.
 *
 * Drop this component into the cluster / recommendation drill-down view.
 * It is self-contained: state, calculation, and markup all live here so it
 * can be inserted without touching surrounding layout, nav, or theme.
 *
 * INTEGRATION:
 *   import PathwayComparison from "./PathwayComparison";
 *   ...
 *   <PathwayComparison clusterName="Cluster 14 — Kolhapur" />
 *
 * To feed it real optimizer output instead of the mock dataset, replace the
 * `PATHWAYS` import in pathwayData.js with a fetch keyed on the active
 * cluster (see the comment block at the top of that file).
 * ---------------------------------------------------------------------------
 */
export default function PathwayComparison({ clusterName }) {
  const [quantity, setQuantity] = useState(100);
  const [customQuantity, setCustomQuantity] = useState("");
  const [isCustom, setIsCustom] = useState(false);
  const [view, setView] = useState("financial"); // "financial" | "environmental"
  const [expandedId, setExpandedId] = useState(null);

  const rows = useMemo(() => calculateForQuantity(quantity, PATHWAYS), [
    quantity,
  ]);

  const sortedRows = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) =>
      view === "financial"
        ? b.netMargin - a.netMargin
        : b.co2Avoided - a.co2Avoided
    );
    return copy;
  }, [rows, view]);

  const maxMargin = Math.max(...rows.map((r) => Math.max(0, r.netMargin)));
  const maxEmissions = Math.max(...rows.map((r) => r.emissions));

  const recommended = rows.find((r) => r.isRecommended);

  const handlePresetClick = (value) => {
    setIsCustom(false);
    setQuantity(value);
  };

  const handleCustomChange = (e) => {
    const val = e.target.value.replace(/[^0-9]/g, "");
    setCustomQuantity(val);
    setIsCustom(true);
    if (val) setQuantity(Number(val));
  };

  const toggleDetails = (id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <section className="pc-root" aria-labelledby="pc-heading">
      <header className="pc-header">
        <div className="pc-heading-group">
          <p className="pc-eyebrow">Feature 03 — Pathway Comparison</p>
          <h2 id="pc-heading" className="pc-title">
            Same tonnage, five outcomes
          </h2>
          <p className="pc-subtitle">
            For the same amount of biomass{clusterName ? ` from ${clusterName}` : ""},
            which pathway pays the most after transport — and avoids the most
            emissions?
          </p>
        </div>

        <div className="pc-view-toggle" role="tablist" aria-label="Comparison view">
          <button
            type="button"
            role="tab"
            aria-selected={view === "financial"}
            className={`pc-toggle-btn ${view === "financial" ? "pc-toggle-btn--active pc-toggle-btn--financial" : ""}`}
            onClick={() => setView("financial")}
          >
            Financial View
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "environmental"}
            className={`pc-toggle-btn ${view === "environmental" ? "pc-toggle-btn--active pc-toggle-btn--environmental" : ""}`}
            onClick={() => setView("environmental")}
          >
            Environmental View
          </button>
        </div>
      </header>

      <div className="pc-quantity-row">
        <span className="pc-quantity-label">Compare for</span>
        <div className="pc-quantity-options">
          {QUANTITY_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              className={`pc-qty-btn ${!isCustom && quantity === preset ? "pc-qty-btn--active" : ""}`}
              onClick={() => handlePresetClick(preset)}
            >
              {preset}
            </button>
          ))}
          <div className={`pc-qty-custom ${isCustom ? "pc-qty-custom--active" : ""}`}>
            <input
              type="text"
              inputMode="numeric"
              placeholder="Custom"
              value={customQuantity}
              onChange={handleCustomChange}
              aria-label="Custom quantity in tonnes"
            />
          </div>
        </div>
        <span className="pc-quantity-label pc-quantity-label--suffix">tonnes</span>
      </div>

      {recommended && (
        <div className="pc-why-box">
          <span className="pc-why-badge">Recommended</span>
          <div>
            <p className="pc-why-title">{recommended.name}</p>
            <p className="pc-why-text">{recommended.whyRecommended}</p>
          </div>
        </div>
      )}

      <div className="pc-table-scroll">
        <table className="pc-table">
          <thead>
            <tr>
              <th scope="col" className="pc-col-sticky">Pathway</th>
              <th scope="col">Revenue</th>
              <th scope="col">Transport</th>
              <th scope="col">Processing</th>
              <th
                scope="col"
                className={view === "financial" ? "pc-col-emphasis" : ""}
              >
                Net Margin
              </th>
              <th scope="col">Emissions</th>
              <th
                scope="col"
                className={view === "environmental" ? "pc-col-emphasis" : ""}
              >
                CO₂ Avoided
              </th>
              <th scope="col">Margin vs Emissions</th>
              <th scope="col" className="pc-col-actions">Details</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => {
              const marginPct = maxMargin > 0 ? Math.max(0, row.netMargin) / maxMargin : 0;
              const emissionsPct = maxEmissions > 0 ? row.emissions / maxEmissions : 0;
              const marginTone = row.isBaseline
                ? "pc-neutral"
                : row.isHighestMargin
                ? "pc-good"
                : row.netMargin <= 0
                ? "pc-bad"
                : "pc-neutral";
              const emissionsTone = row.isBaseline
                ? "pc-bad"
                : row.isLowestEmissions
                ? "pc-good"
                : "pc-neutral";

              return (
                <React.Fragment key={row.id}>
                  <tr
                    className={`pc-row ${row.isRecommended ? "pc-row--recommended" : ""} ${row.isBaseline ? "pc-row--baseline" : ""}`}
                  >
                    <th scope="row" className="pc-col-sticky pc-pathway-cell">
                      <span className="pc-pathway-name">{row.shortLabel}</span>
                      <span className="pc-badge-group">
                        {row.isRecommended && (
                          <span className="pc-badge pc-badge--recommended">Recommended</span>
                        )}
                        {row.isHighestMargin && !row.isBaseline && (
                          <span className="pc-badge pc-badge--good">Highest margin</span>
                        )}
                        {row.isLowestEmissions && !row.isBaseline && (
                          <span className="pc-badge pc-badge--good">Lowest emissions</span>
                        )}
                        {row.isBaseline && (
                          <span className="pc-badge pc-badge--baseline">Baseline</span>
                        )}
                      </span>
                    </th>
                    <td data-label="Revenue">{formatCurrency(row.revenue)}</td>
                    <td data-label="Transport">{formatCurrency(row.transportCost)}</td>
                    <td data-label="Processing">{formatCurrency(row.processingCost)}</td>
                    <td
                      data-label="Net Margin"
                      className={`pc-metric ${marginTone} ${view === "financial" ? "pc-col-emphasis" : ""}`}
                    >
                      {formatCurrency(row.netMargin)}
                    </td>
                    <td data-label="Emissions">{formatTonnes(row.emissions)}</td>
                    <td
                      data-label="CO2 Avoided"
                      className={`pc-metric ${emissionsTone} ${view === "environmental" ? "pc-col-emphasis" : ""}`}
                    >
                      {formatTonnes(row.co2Avoided)}
                    </td>
                    <td data-label="Margin vs Emissions" className="pc-bars-cell">
                      <div className="pc-scale" aria-hidden="true">
                        <div className="pc-scale-track pc-scale-track--margin">
                          <div
                            className="pc-scale-fill pc-scale-fill--margin"
                            style={{ width: `${marginPct * 100}%` }}
                          />
                        </div>
                        <div className="pc-scale-track pc-scale-track--emissions">
                          <div
                            className="pc-scale-fill pc-scale-fill--emissions"
                            style={{ width: `${emissionsPct * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td data-label="Details" className="pc-col-actions">
                      <button
                        type="button"
                        className="pc-details-btn"
                        aria-expanded={expandedId === row.id}
                        onClick={() => toggleDetails(row.id)}
                      >
                        {expandedId === row.id ? "Hide" : "View"}
                      </button>
                    </td>
                  </tr>
                  {expandedId === row.id && (
                    <tr className="pc-detail-row">
                      <td colSpan={9}>
                        <div className="pc-detail-panel">
                          <div className="pc-detail-col">
                            <p className="pc-detail-label">Revenue</p>
                            <p className="pc-detail-text">{row.details.revenueNote}</p>
                          </div>
                          <div className="pc-detail-col">
                            <p className="pc-detail-label">Transport cost</p>
                            <p className="pc-detail-text">{row.details.transportNote}</p>
                          </div>
                          <div className="pc-detail-col">
                            <p className="pc-detail-label">Processing cost</p>
                            <p className="pc-detail-text">{row.details.processingNote}</p>
                          </div>
                          <div className="pc-detail-col">
                            <p className="pc-detail-label">Net margin formula</p>
                            <p className="pc-detail-text pc-detail-formula">{row.details.marginFormula}</p>
                          </div>
                          <div className="pc-detail-col">
                            <p className="pc-detail-label">Emissions basis</p>
                            <p className="pc-detail-text">{row.details.emissionsNote}</p>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="pc-footnote">
        Figures shown are for {quantity || 0} tonnes of feedstock, calculated
        from per-tonne rates. Demo values — replace with live optimizer output
        per cluster.
      </p>
    </section>
  );
}
