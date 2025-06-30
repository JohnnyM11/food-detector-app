// Einstiegspunkt für die React-App
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// seit React 18 neue Root-API: createRoot() statt nur render()
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />             {/* Hauptkomponente*/}
  </React.StrictMode>
);
