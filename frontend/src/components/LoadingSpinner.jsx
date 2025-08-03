import React from "react";

function LoadingSpinner() {
  return (
    <div className="loading-dots-container">
      <span className="loading-label">Lädt</span>
      <div className="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  );
}

export default LoadingSpinner;
