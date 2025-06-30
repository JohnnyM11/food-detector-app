import React, { useState } from "react";

function FeedbackForm({ onSubmit }) {
  const [correction, setCorrection] = useState("");   // User-Korrektur (z.B. Apfel statt Bananae)
  const [showInput, setShowInput] = useState(false);  // Eingabemaske anzeigen

  const handleDislike = () => setShowInput(true);     // bei Klick auf Daumen-runter
  const handleSubmit = () => {
    onSubmit(correction);       // Rückgabe an App
    setCorrection("");          // Eingabe leeren
    setShowInput(false);        // Eingabefeld ausblenden
  };

  return (
    <div>
      <button onClick={() => onSubmit("like")}>👍</button>
      <button onClick={handleDislike}>👎</button>

      {showInput && (
        <div>
          <input
            type="text"
            placeholder="Korrektur z. B. 'Apfel'"
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
          />
          <button onClick={handleSubmit}>Senden</button>
        </div>
      )}
    </div>
  );
}

export default FeedbackForm;
