#!/bin/bash

echo "👉 Build containers..."
docker compose build

echo "👉 Up containers..."
docker compose up -d

echo "✅ Deploy production completato!"