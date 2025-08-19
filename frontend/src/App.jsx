import React, { useState, useEffect } from "react";
import ImageUploader from "./components/ImageUploader";
import ResultDisplay from "./components/ResultDisplay";
import FeedbackForm from "./components/FeedbackForm";
import LoadingSpinner from "./components/LoadingSpinner";

function App() {
  const [result, setResult] = useState({ items: [], image_id: "" }); // speichert API-Ergebnis im State
  const [loading, setLoading] = useState(false); // Ladeanzeige im State
  const [modelName, setModelName] = useState(""); // Modellname im State
  const VERSION = "V1.2"; // Versionierung

  // Modellname vom Backend holen
  useEffect(() => {
  const fetchModelInfo = async () => {
   try {
     const res = await fetch(`${import.meta.env.VITE_API_URL}/model-info`);
     if (!res.ok) throw new Error(`HTTP ${res.status}`);
     const data = await res.json();
     setModelName(data.model);
   } catch (err) {
     console.error("Model-Info fetch failed:", err);
     setModelName("unbekannt"); // UI stürzt nicht ab
   }
  };
  fetchModelInfo();
}, []);


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
    <div style={{ fontFamily: "Arial" }}>
      <h1 style={{ marginBottom: "4px" }}>Food Detector </h1>
      <div style={{ fontSize: "0.9em", color: "#666", marginBottom: "20px" }}>
        {VERSION} (Modell: {modelName})
      </div>

      {/* Bild-Upload und Bildnamen mit in result einfügen */}
      <ImageUploader
        onResult={(data, fileName) =>
          setResult({ ...data, image_id: fileName })
        }
        setLoading={setLoading} // Ladeanzeige aktivieren
      />

      {/* Ladeanzeige */}
      {loading && (
        <div className="loading-container">
          <LoadingSpinner />
        </div>
      )}

      {/* Ausgabe der Erkennung */}
      <ResultDisplay items={result?.items} />

      {/* Feedback */}
      {result?.items?.length > 0 && <FeedbackForm onSubmit={handleFeedback} />}
    </div>
  );
}

export default App;
