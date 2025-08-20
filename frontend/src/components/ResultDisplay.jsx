// frontend/src/components/ResultDisplay.jsx
import React from "react";

// Kleine Format‑Helper fürs UI
const fmt = (v, unit = "") =>
  v === null || v === undefined ? "–" : `${v}${unit}`;
const pct = (p) =>
  p === null || p === undefined ? "–" : `${(p * 100).toFixed(1)}%`;

/**
 * UI‑Komponente für die Nährwerte‑Box
 * Erwartet das Objekt, das der Backend‑Key "nutrition_per_100g" liefert:
 * {
 *   product_name, energy_kj, energy_kcal, fat_g, carbs_g, sugars_g, protein_g, source
 * }
 */
function NutritionBox({ data }) {
  // Wenn das Backend nichts gefunden hat (null), zeige einen knappen Hinweis
  if (!data) {
    return (
      <div style={styles.card}>
        <p style={styles.cardTitle}>Nährwerte pro 100 g</p>
        <p style={styles.muted}>Keine Nährwerte gefunden.</p>
      </div>
    );
  }

  const {
    product_name,
    energy_kj,
    energy_kcal,
    fat_g,
    carbs_g,
    sugars_g,
    protein_g,
    source,
  } = data;

  return (
    <div style={styles.card}>
      <p style={styles.cardTitle}>Nährwerte pro 100 g</p>
      {/* Optional: OFF-Produktname, falls vorhanden */}
      {product_name ? (
        <p style={styles.refLine}>
          <span style={{ fontWeight: 600 }}>Referenz:</span> {product_name}
        </p>
      ) : null}

      <ul style={styles.list}>
        <li>
          Energie: {fmt(energy_kj, " kJ")} ({fmt(energy_kcal, " kcal")})
        </li>
        <li>Fett: {fmt(fat_g, " g")}</li>
        <li>
          Kohlenhydrate (davon Zucker): {fmt(carbs_g, " g")} (
          {fmt(sugars_g, " g")})
        </li>
        <li>Eiweiß: {fmt(protein_g, " g")}</li>
      </ul>

      <p style={styles.source}>Quelle: {source || "OpenFoodFacts"}</p>
    </div>
  );
}

/**
 * Hauptkomponente: listet erkannte Items (Label + Confidence + Nährwerte)
 * Erwartet von App.jsx: <ResultDisplay items={result?.items} />
 * Jedes item hat mind. { label, confidence } und optional { bbox, nutrition_per_100g }
 */
export default function ResultDisplay({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <div style={{ textAlign: "left", marginTop: 16 }}>
      <h2>Erkannte Objekte:</h2>

      {items.map((item, idx) => (
        <div key={idx} style={styles.itemCard}>
          <div style={styles.itemHeader}>
            <strong style={{ fontSize: 16 }}>
              {item.label ?? "Unbekannt"}
            </strong>
            <span style={styles.conf}>Sicherheit: {pct(item.confidence)}</span>
          </div>

          {/* Falls später Bounding Boxes angezeigt werden sollen: item.bbox als [x1,y1,x2,y2] */}
          {/* <pre>{JSON.stringify(item.bbox)}</pre> */}

          {/* Nährwerte-Box, füttern mit item.nutrition_per_100g (kann null sein) */}
          <NutritionBox data={item.nutrition_per_100g} />
        </div>
      ))}
    </div>
  );
}

// Inline‑Styles (leichtgewichtig, damit keine extra CSS-Datei nötig ist)
const styles = {
  itemCard: {
    border: "1px solid rgba(0,0,0,0.1)",
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    background: "rgba(255,255,255,0.8)",
  },
  itemHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 8,
  },
  conf: {
    fontSize: 12,
    color: "#555",
  },
  card: {
    border: "1px solid rgba(0,0,0,0.08)",
    borderRadius: 10,
    padding: "10px 12px",
    background: "rgba(255,255,255,0.6)",
  },
  cardTitle: {
    margin: "0 0 6px 0",
    fontWeight: 700,
  },
  refLine: {
    margin: "0 0 6px 0",
    fontSize: 13,
  },
  list: {
    margin: "0 0 6px 16px",
    padding: 0,
    lineHeight: 1.7,
    fontSize: 14,
  },
  source: {
    margin: 0,
    fontSize: 11,
    color: "#666",
  },
};
