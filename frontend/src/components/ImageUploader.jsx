import React, { useState } from "react";

function ImageUploader({ onResult }) {
  const [image, setImage] = useState(null);       // Vorschau für Anzeige
  const [loading, setLoading] = useState(false);  // Ladeanzeige

  // Bild auswählen und an API senden
  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    setImage(URL.createObjectURL(file));      // Vorschau anzeigen

    // Vorbereitung für API-Request
    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);   // Start Ladeanzeige
    // POST an /predict-Endpunkt
    const res = await fetch(`${import.meta.env.VITE_API_URL}/predict`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    onResult(data);                           // Ergebnis an App zurückgeben
    setLoading(false);    // Ende Ladeanzeige
  };

  return (
    <div>
      <input type="file" accept="image/*" onChange={handleFileChange} />
      {image && <img src={image} alt="Preview" width="200" />}
    </div>
  );
}

export default ImageUploader;
