# Opening Weekend Intelligence — Streamlit edition

A standalone Streamlit replica of the front page (Business view) of the SPCS
`OW_INTELLIGENCE` app: browse upcoming/past films, see each film's predicted
opening weekend, tier, bear/bull range with a probability-density curve,
Large+ breakout odds, per-tier confidence, and the model's summary.

Runs on **Streamlit Community Cloud (free tier)** — no Snowflake connection
required. It reads a **static snapshot** of the model output in `data/films.json`.

## Run locally

```bash
python3 -m streamlit run streamlit_app.py
```

## Deploy to your free Streamlit account

1. Create a new GitHub repo and push this folder:
   ```bash
   git remote add origin https://github.com/<you>/ow-intelligence-streamlit.git
   git push -u origin main
   ```
2. Go to https://share.streamlit.io → **Create app** → pick this repo,
   branch `main`, main file `streamlit_app.py` → **Deploy**.

## Refreshing the data

The app is a point-in-time snapshot. To update predictions/box office, copy a
fresh `films.json` from the SPCS app and push:

```bash
cp ~/box-office-demo/data/films.json data/films.json
git commit -am "refresh films snapshot" && git push
```

## What's not included

The SPCS app's **Data Science** and **Validation** tabs are omitted — Validation
queries Snowflake live (SPCS-only) and won't work on the free tier without
configured secrets. This app replicates the Business landing page only.
