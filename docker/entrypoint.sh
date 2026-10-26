#!/bin/sh
# Prepare the database and start the app (decision D-022).
# Downloads kept in data/reviews/ that are not in the database yet are imported and classified, so a new
# PostgreSQL database fills itself from the JSON files on its first start.
set -e
python pipeline/import_reviews.py
python pipeline/predict_reviews.py
exec streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true
