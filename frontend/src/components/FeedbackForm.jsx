import React, { useState } from "react";

// Liste der Labels (später evtl. per API vom Backend laden)
const LABELS = ["Apfel", "Banane", "Birne", "Orange", "Tomate", "Brokkoli"];

function FeedbackForm({ onSubmit }) {
  const [showInput, setShowInput] = useState(false); // Dropdown anzeigen?
  const [selectedLabel, setSelectedLabel] = useState(""); // User-Korrektur (z.B. Apfel statt Bananae)

  const handleDislike = () => setShowInput(true); // Anzeigen bei Klick auf Daumen-runter
  const handleSubmit = () => {
    if (!selectedLabel) return;
    onSubmit(selectedLabel); // Rückgabe der Auswahl an App
    selectedLabel(""); // Eingabe leeren
    setShowInput(false); // Dropdown ausblenden
  };

  return (
    <div>
      <button onClick={() => onSubmit("like")}>👍</button>
      <button onClick={handleDislike}>👎</button>

      {showInput && (
        <div>
          <label htmlFor="correction">Korrekte Auswahl:</label>
          <select
            id="correction"
            value={selectedLabel}
            onChange={(e) => setSelectedLabel(e.target.value)}
          >
            <option value="">Bitte wählen…</option>
            {LABELS.map((label, index) => (
              <option key={index} value={label}>
                {label}
              </option>
            ))}
          </select>
          <button onClick={handleSubmit}>Senden</button>
        </div>
      )}
    </div>
  );
}

export default FeedbackForm;
