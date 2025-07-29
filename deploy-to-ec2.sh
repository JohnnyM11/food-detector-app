#!/bin/bash

echo "🔼 Pushing local changes..."
git add .
git commit -m "🔄 Deploy update"
git push origin main || { echo "❌ Push failed"; exit 1; }

echo "🚀 Deploying on EC2..."
ssh -i ".\OneDrive\_Studium Coburg\10. Semester Bachelorarbeit\Bachelorarbeit\_Bachelorarbeit\AWS\KeyPair_JM.pem" ec2-user@63.178.179.86 '~/deploy.sh'
