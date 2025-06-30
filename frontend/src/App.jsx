import React, { useState } from "react";
import ImageUploader from "./components/ImageUploader";
import ResultDisplay from "./components/ResultDisplay";
import FeedbackForm from "./components/FeedbackForm";

function App() {
  const [result, setResult] = useState(null);                 // speichert API-Ergebnis

  const handleFeedback = (value) => {
    console.log("Feedback:", value);
    // TODO: später an API ( /feedback-Endpoint ) senden
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>Food Detector</h1>
      <ImageUploader onResult={setResult} />                  {/* Bild-Upload */}
      <ResultDisplay items={result?.items} />                 {/* Ausgabe der Erkennung */}
      {result && <FeedbackForm onSubmit={handleFeedback} />}  {/* Feedback */}
    </div>
  );
}

export default App;
