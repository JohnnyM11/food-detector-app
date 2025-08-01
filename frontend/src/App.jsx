import React, { useState } from "react";
import ImageUploader from "./components/ImageUploader";
import ResultDisplay from "./components/ResultDisplay";
import FeedbackForm from "./components/FeedbackForm";
import LoadingSpinner from "./components/LoadingSpinner";

function App() {
  const [result, setResult] = useState({ items: [], image_id: "" }); // speichert API-Ergebnis
  const [loading, setLoading] = useState(false); // Ladeanzeige

  const handleFeedback = async (input) => {
    const original = result?.items?.[0]?.label || "unbekannt";
    const confidence = result?.items?.[0]?.confidence || null;
    const image_id = result?.image_id || "unbekannt.jpg";

    const correction = typeof input == "string" ? input : input.correction; // Wenn nur ein Label übergeben wurde, umwandeln in Objekt

    const payload = {
      "1. original": original,
      "2. correction": correction,
      "3. confidence": confidence,
      "4. image_id": image_id,
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
      {/* Bild-Upload und Bildnamen mit in result einfügen */}
      <ImageUploader
        onResult={(data, fileName) =>
          setResult({ ...data, image_id: fileName })
        }
        setLoading={setLoading} // Ladeanzeige aktivieren
      />
      {/* Ladeanzeige */}
      {loading && <LoadingSpinner />}
      {/* Ausgabe der Erkennung */}
      <ResultDisplay items={result?.items} />
      {/* Feedback */}
      {result?.items?.length > 0 && <FeedbackForm onSubmit={handleFeedback} />}
    </div>
  );
}

export default App;
