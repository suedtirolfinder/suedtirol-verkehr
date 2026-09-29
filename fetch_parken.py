name: Update Parkdaten

on:
  schedule:
    - cron: '*/15 * * * *'
  workflow_dispatch:

jobs:
  update-data:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Python einrichten
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Beide Skripte ausführen (Parken & Verkehr)
        run: |
          python fetch_parken.py
          python fetch_verkehr.py

      - name: Änderungen committen und pushen
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add parken.json verkehr.json
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-Update Park- und Verkehrsdaten" && git push)
