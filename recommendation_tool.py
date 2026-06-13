"""
Route engine for the Rewards Redemption Optimizer.

Reads flight rows from a SQLite database and builds candidate routes between an
origin and destination, including synthetic (layover) routes through any hub that
connects the two on a given day. Routes are scored by value per mile:

    value per mile = (cash price - taxes/fees) / miles redeemed   (in cents)

The same engine powers both the command-line tool (one date, best route) and the
Streamlit app (a date range returned as a DataFrame).

Note: the bundled database is a *synthetic sample* dataset (August 2025, a handful
of routes) used to demonstrate the engine. It is not live airline pricing.
"""

import re
import sqlite3
from datetime import datetime, timedelta

import pandas as pd

DB_PATH = "travel_data_with_miles.db"

# routes treated as international, which carry higher taxes/fees. The dataset has
# no per-flight fee field, so we estimate it from the route.
INTERNATIONAL_ROUTES = {("JFK", "LHR"), ("DXB", "LHR"), ("LAX", "HND")}
INTERNATIONAL_FEE = 50.00
DOMESTIC_FEE = 11.20

_FLIGHT_COLUMNS = ["date", "type", "origin", "destination", "airline", "price",
                   "miles", "taxes", "value_per_mile_cents", "route", "flights_json"]


def calculate_value_per_mile(cash_price, taxes_and_fees, miles_used):
    """Cents of cash value unlocked per mile redeemed. Higher is a better deal."""
    if miles_used == 0:
        raise ValueError("Miles used cannot be zero.")
    return round((cash_price - taxes_and_fees) / miles_used * 100, 2)


def estimate_taxes_and_fees(origin, destination):
    """Estimate taxes/fees for a leg (the dataset has no explicit fee column)."""
    if (origin, destination) in INTERNATIONAL_ROUTES:
        return INTERNATIONAL_FEE
    return DOMESTIC_FEE


# ---- database helpers (one connection passed in, reused across queries) ----
def _query_legs(conn, origin, destination, date):
    """All flights for an exact origin/destination/date."""
    cur = conn.execute(
        """
        SELECT airline, flight_number, departure_time, arrival_time, price, miles
        FROM flights
        WHERE route_origin = ? AND route_destination = ? AND date = ?
        """,
        (origin, destination, date),
    )
    return cur.fetchall()


def _possible_hubs(conn, origin, destination, date):
    """Airports reachable from the origin that also reach the destination that day."""
    from_origin = {row[0] for row in conn.execute(
        "SELECT DISTINCT route_destination FROM flights WHERE route_origin = ? AND date = ?",
        (origin, date),
    )}
    to_destination = {row[0] for row in conn.execute(
        "SELECT DISTINCT route_origin FROM flights WHERE route_destination = ? AND date = ?",
        (destination, date),
    )}
    return sorted(from_origin & to_destination)


def _leg_dict(leg):
    """Turn a raw flight row into a serializable leg record."""
    airline, flight_number, dep, arr, price, miles = leg
    return {
        "airline": airline,
        "flight_number": flight_number,
        "departure_time": dep,
        "arrival_time": arr,
        "price": float(price),
        "miles": int(miles),
    }


# ---- option building (shared by both entry points) -------------------------
def collect_options(conn, origin, destination, date, include_synthetic=True,
                    min_layover_minutes=45):
    """
    Build every candidate route (direct + synthetic) for a single date as a list
    of option dicts with a consistent schema.
    """
    options = []

    # direct flights
    for leg in _query_legs(conn, origin, destination, date):
        airline, _, _, _, price, miles = leg
        taxes = estimate_taxes_and_fees(origin, destination)
        options.append({
            "date": date,
            "type": "Direct",
            "origin": origin,
            "destination": destination,
            "airline": airline,
            "price": float(price),
            "miles": int(miles),
            "taxes": float(taxes),
            "value_per_mile_cents": calculate_value_per_mile(float(price), taxes, int(miles)),
            "route": [(origin, destination)],
            "flights_json": [_leg_dict(leg)],
        })

    # synthetic (one-stop) routes
    if include_synthetic:
        for hub in _possible_hubs(conn, origin, destination, date):
            first_legs = _query_legs(conn, origin, hub, date)
            second_legs = _query_legs(conn, hub, destination, date)
            for leg1 in first_legs:
                arrival = datetime.fromisoformat(leg1[3])
                for leg2 in second_legs:
                    departure = datetime.fromisoformat(leg2[2])
                    # second leg must depart after a minimum connection window
                    if departure <= arrival + timedelta(minutes=min_layover_minutes):
                        continue
                    total_price = float(leg1[4]) + float(leg2[4])
                    total_miles = int(leg1[5]) + int(leg2[5])
                    taxes = (estimate_taxes_and_fees(origin, hub)
                             + estimate_taxes_and_fees(hub, destination))
                    options.append({
                        "date": date,
                        "type": "Synthetic",
                        "origin": origin,
                        "destination": destination,
                        "airline": f"{leg1[0]}+{leg2[0]}",
                        "price": total_price,
                        "miles": total_miles,
                        "taxes": float(taxes),
                        "value_per_mile_cents": calculate_value_per_mile(total_price, taxes, total_miles),
                        "route": [(origin, hub), (hub, destination)],
                        "flights_json": [_leg_dict(leg1), _leg_dict(leg2)],
                    })

    return options


# ---- public API ------------------------------------------------------------
def recommend_best_route(origin, destination, date, include_synthetic=True,
                         min_layover_minutes=45, db_path=DB_PATH):
    """Single best route (by value per mile) for one date, or a message if none."""
    with sqlite3.connect(db_path) as conn:
        options = collect_options(conn, origin, destination, date,
                                  include_synthetic, min_layover_minutes)
    if not options:
        return "No flights available for that day."
    return max(options, key=lambda opt: opt["value_per_mile_cents"])


def recommend_routes(origin, destination, start_date, end_date,
                     include_synthetic=True, min_layover_minutes=45,
                     objective="vpm", min_vpm_cents=None, max_price=None,
                     airline_allowlist=None, max_results=100, db_path=DB_PATH):
    """
    All candidate routes across a date range as a DataFrame, filtered and sorted
    for the UI. Columns: see _FLIGHT_COLUMNS.
    """
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    if end < start:
        start, end = end, start

    rows = []
    with sqlite3.connect(db_path) as conn:
        day = start
        while day <= end:
            rows.extend(collect_options(conn, origin, destination, day.isoformat(),
                                        include_synthetic, min_layover_minutes))
            day += timedelta(days=1)

    df = pd.DataFrame(rows, columns=_FLIGHT_COLUMNS)  # fixed schema even when empty
    if df.empty:
        return df

    # filters
    if min_vpm_cents is not None:
        df = df[df["value_per_mile_cents"] >= float(min_vpm_cents)]
    if max_price is not None:
        df = df[df["price"] <= float(max_price)]
    if airline_allowlist:
        patterns = [re.escape(str(a).strip()) for a in airline_allowlist if str(a).strip()]
        if patterns:
            df = df[df["airline"].str.contains("|".join(patterns), case=False, na=False)]

    # objective sort
    if objective == "min_fees":
        df = df.sort_values(["taxes", "price", "value_per_mile_cents"],
                            ascending=[True, True, False])
    else:
        df = df.sort_values(["value_per_mile_cents", "price"], ascending=[False, True])

    if max_results:
        df = df.head(int(max_results))
    return df.reset_index(drop=True)


# ---- command-line interface ------------------------------------------------
def _run_cli():
    print("Flight Recommendation Tool")
    origin = input("Enter origin airport code (e.g., LAX): ").upper()
    destination = input("Enter destination airport code (e.g., JFK): ").upper()
    date = input("Enter travel date (YYYY-MM-DD): ")

    raw = input("Minimum layover (minutes, default 45): ").strip()
    try:
        min_layover = int(raw) if raw else 45
        if min_layover < 0:
            print("Layover can't be negative; using 45.")
            min_layover = 45
    except ValueError:
        print("Invalid number; using 45.")
        min_layover = 45

    result = recommend_best_route(origin, destination, date, min_layover_minutes=min_layover)

    print("\nBest Flight Option:")
    if isinstance(result, str):
        print(result)
        return
    print("Type:", result["type"])
    legs = [origin] + [leg[1] for leg in result["route"]]
    print("Route:", " -> ".join(legs))
    print(f"Total Price: ${result['price']:.2f}")
    print("Flights:")
    for leg in result["flights_json"]:
        print(f"  {leg['airline']} {leg['flight_number']} | "
              f"Dep: {leg['departure_time']} -> Arr: {leg['arrival_time']} | "
              f"${leg['price']:.2f} | {leg['miles']} miles")
    print(f"Taxes and Fees: ${result['taxes']:.2f}")
    print(f"Value per Mile: {result['value_per_mile_cents']} cents")


if __name__ == "__main__":
    _run_cli()
