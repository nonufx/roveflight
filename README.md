# Rewards Redemption Optimizer

A Streamlit app that finds the best-value airline routes when paying with miles
versus cash. It ranks both direct flights and synthetic (one-stop) itineraries by
**value per mile**:

```
value per mile = (cash price - taxes/fees) / miles redeemed   (in cents)
```

A higher value per mile means each mile is buying more cash value, so it's a
better redemption.

## About the data

The bundled SQLite database (`travel_data_with_miles.db`) holds ~860 flights
across a handful of routes in August 2025. It is a **mix of real flight data
collected via a flight-pricing API and synthetic data generated to fill coverage
gaps** once the API rate limits were reached. It is meant to demonstrate the
routing and scoring engine, not to serve as a complete or live pricing source.
Because part of the data is generated, some quirks exist (for example, synthetic
one-stop routes often score better than directs because their generated mileage
costs are lower).

`clean_airline_names.py` is the one-off, seeded script used to replace leftover
placeholder/test airline names from the generated rows with real carriers that
operate the same routes, so the dataset stays realistic and consistent.

## How the engine works

1. **Direct flights**: query the database for flights matching the origin,
   destination, and date.
2. **Synthetic routes**: find any hub that the origin reaches and that also
   reaches the destination on the same day, then pair first and second legs that
   leave enough connection time (a configurable minimum layover).
3. **Scoring**: compute value per mile for each option (summing price, miles, and
   estimated taxes across legs for synthetic routes).
4. **Ranking and filtering**: sort by value per mile (or minimum fees), with
   optional filters for price ceiling, airline allow-list, and miles balance.

The same engine (`recommendation_tool.py`) powers both the command-line tool and
the Streamlit app.

## Features

- Direct and synthetic (one-stop) route search across a date range
- Value-per-mile ranking, or a minimum-fees objective
- Filters: price ceiling, airline allow-list, miles balance, minimum layover
- Results table with per-leg detail and CSV export
- Top-routes bar chart and a price-vs-miles scatter plot
- Optional airport map (requires `airports.csv` with `iata,lat,lon` columns)

## Project structure

- `streamlit_app.py`: the web UI
- `recommendation_tool.py`: the route engine (CLI + DataFrame API)
- `clean_airline_names.py`: one-off data cleanup script
- `travel_data_with_miles.db`: synthetic sample database
- `airports.csv`: airport coordinates for the optional map
- `style.css`: minimal styling

## Running it

```bash
pip install -r requirements.txt   # or: streamlit, pandas, numpy, pydeck

# web app
streamlit run streamlit_app.py

# command-line version
python recommendation_tool.py
```

## Disclaimer

For educational and demonstration purposes only. The data is partly synthetic and
the output is not real travel or financial advice.
