import React, { useState } from "react";
import ImageUploader from "./components/ImageUploader";
import ResultDisplay from "./components/ResultDisplay";
import FeedbackForm from "./components/FeedbackForm";

function App() {
  const [result, setResult] = useState(null); // speichert API-Ergebnis

  const handleFeedback = async (correctionLabel) => {
    console.log("Feedback:", correctionLabel);

    const original = result?.items?.[0]?.label || "unbekannt";
    const confidence = result?.items?.[0]?.confidence || null;

    const payload = {
      original: original,
      correction: correctionLabel,
      confidence: confidence,
      image_id: "example.jpg", // Platzhalter, später ggf. echte ID
    };

    await fetch(`${import.meta.env.VITE_API_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    alert("Danke für dein Feedback!");
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>Food Detector</h1>
      <ImageUploader onResult={setResult} /> {/* Bild-Upload */}
      <ResultDisplay items={result?.items} /> {/* Ausgabe der Erkennung */}
      {result && <FeedbackForm onSubmit={handleFeedback} />} {/* Feedback */}
    </div>
  );
}

export default App;
