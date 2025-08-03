import React from "react";
import "../App.css"; // sicherstellen, dass das CSS eingebunden ist

function LoadingSpinner() {
  return (
    <div className="loading-dots-container">
      <span className="loading-label">Lädt</span>
      <div className="loading-dots">
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    </div>
  );
}

export default LoadingSpinner;
