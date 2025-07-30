#!/bin/bash

# Fallback auf "main", falls kein Branch angegeben
BRANCH=${1:-main}
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")

echo "🔁 Aktueller Branch: $BRANCH"
echo "🔼 Commit und Push mit Zeitstempel..."

# Git-Vorgänge lokal
git checkout "$BRANCH" || { echo "❌ Branch '$BRANCH' existiert nicht."; exit 1; }
git add .
git commit -m "🔄 Deploy $BRANCH ($TIMESTAMP)"
git push origin "$BRANCH" || { echo "❌ Push fehlgeschlagen."; exit 1; }

echo "🚀 Deploy auf EC2 wird ausgeführt..."
ssh -i "C:/Users/JM11/OneDrive/_Studium Coburg/10. Semester Bachelorarbeit/Bachelorarbeit/_Bachelorarbeit/AWS/KeyPair_JM.pem" ec2-user@63.178.179.86 "~/deploy.sh $BRANCH"

# Merge-Abfrage (nur wenn nicht main)
if [ "$BRANCH" != "main" ]; then
  echo ""
  read -p "Möchtest du den Branch '$BRANCH' jetzt mit 'main' mergen? (y/n): " MERGE

  if [ "$MERGE" == "y" ]; then
    echo "🔀 Merge wird durchgeführt..."
    git checkout main
    git merge "$BRANCH"
    git push origin main
    git checkout "$BRANCH"
    echo "✅ Merge abgeschlossen und in main gepusht."
  else
    echo "🚫 Kein Merge durchgeführt. Bleibe auf Branch '$BRANCH'."
  fi
else
  echo "📦 Branch ist bereits main – kein Merge nötig."
fi
