import React from "react";

// Gibt erkannte Lebensmittel + Nährwerte aus
function ResultDisplay({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <div>
      <h2>Erkannt:</h2>
      {items.map((item, idx) => (
        <div key={idx}>
          <strong>{item.label}</strong> ({(item.confidence * 100).toFixed(1)}%)
          <ul>
            <li>Kalorien: {item.nutrition.kcal}</li>
            <li>Protein: {item.nutrition.protein}g</li>
            <li>Fett: {item.nutrition.fat}g</li>
            <li>Kohlenhydrate: {item.nutrition.carbs}g</li>
          </ul>
        </div>
      ))}
    </div>
  );
}

export default ResultDisplay;
