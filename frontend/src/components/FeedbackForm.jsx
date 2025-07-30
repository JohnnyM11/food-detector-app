import React, { useState, useEffect } from "react";       // useEffect lädt Daten einmal beim Laden der Komponente

// Liste der Labels (später evtl. per API vom Backend laden)
//const LABELS = ["Apfel", "Banane", "Birne", "Orange", "Tomate", "Brokkoli", "Keines davon"];

function FeedbackForm({ onSubmit }) {
  const [showInput, setShowInput] = useState(false);      // Dropdown anzeigen? Wird true bei Daumen runter
  const [selectedLabel, setSelectedLabel] = useState(""); // User-Korrektur (z.B. Apfel statt Banane) übers Dropdown
  const [labelOptions, setLabelOptions] = useState("");   // Die vom Backend geladenen Labels (Dropdown-Auswahl)

  useEffect(() => {                                       // useEffect() wird beim ersten Laden der Komponente aufgerufen
    // Labels vom Backend laden
    const fetchLabels = async () => {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/labels`);    // fetch() holt JSON-Daten von der API (/labels)
      const data = await res.json();
      setLabelOptions(data.labels);                       // Liste im State speichern
    };

    fetchLabels();                                        // sofort ausführen
  }, []);                                                 // [] = nur 1x beim Mount ausführen

  const handleDislike = () => setShowInput(true);         // Dropdown anzeigen bei Klick auf Daumen runter
  
  const handleSubmit = () => {                            // Senden/Submit Button gedrückt
    if (!selectedLabel) return;
    onSubmit(selectedLabel);                              // Rückgabe der Auswahl an App
    selectedLabel("");                                    // Dropdown-Auswahl zurücksetzen
    setShowInput(false);                                  // Dropdown ausblenden
  };

  return (
    <div>
      <button onClick={() => onSubmit("like")}>👍</button>      {/*Daumen hoch direkt als "like" übergeben */}
      <button onClick={handleDislike}>👎</button>               {/*Zeigt das Dropdown an */}

      {showInput && (
        <div>
          <label htmlFor="correction">Korrekte Auswahl:</label>
          <select
            id="correction"
            value={selectedLabel}
            onChange={(e) => setSelectedLabel(e.target.value)}
          >
            <option value="">Bitte wählen…</option>
            {labelOptions.map((label, index) => (         // Baut die Dropdown-Einträge dynamisch basierend auf Backend-Antwort
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
