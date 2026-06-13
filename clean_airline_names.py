"""
One-off data cleanup: replace placeholder/test airline names left over from the
synthetic data generator (e.g. "FakeAir", "TestJet", "StarFly") with real
carriers that already operate the same route in the dataset.

This keeps the synthetic dataset realistic and internally consistent. It is
seeded so the result is reproducible. Run once:  python clean_airline_names.py
"""

import random
import sqlite3

DB = "travel_data_with_miles.db"
SEED = 42

# placeholder / test names that should never appear to a user
JUNK_NAMES = {
    "FakeAir", "FakeJet", "FakeFlyer", "TestJet", "AirTest", "RealDirect",
    "QuickConnect", "DirectX", "StarFly", "SkyLynx", "JetBliss", "Nimbus Air",
    "AeroNova", "JetPrime", "FlyZest", "BudgetJet", "BudgetFly", "EconoAir",
    "EagleAir",
}


def main():
    random.seed(SEED)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # real carriers per route, so a replacement is always plausible for that route
    cur.execute("SELECT DISTINCT route_origin, route_destination, airline FROM flights")
    real_by_route = {}
    for origin, dest, airline in cur.fetchall():
        if airline not in JUNK_NAMES:
            real_by_route.setdefault((origin, dest), set()).add(airline)

    # global fallback pool in case a route has only junk carriers
    cur.execute("SELECT DISTINCT airline FROM flights")
    real_pool = sorted(a for (a,) in cur.fetchall() if a not in JUNK_NAMES)

    cur.execute(
        "SELECT id, route_origin, route_destination FROM flights WHERE airline IN (%s)"
        % ",".join("?" * len(JUNK_NAMES)),
        tuple(JUNK_NAMES),
    )
    rows = cur.fetchall()

    updated = 0
    for row_id, origin, dest in rows:
        choices = sorted(real_by_route.get((origin, dest), set())) or real_pool
        replacement = random.choice(choices)
        cur.execute("UPDATE flights SET airline = ? WHERE id = ?", (replacement, row_id))
        updated += 1

    conn.commit()

    # report
    cur.execute(
        "SELECT COUNT(*) FROM flights WHERE airline IN (%s)" % ",".join("?" * len(JUNK_NAMES)),
        tuple(JUNK_NAMES),
    )
    remaining = cur.fetchone()[0]
    conn.close()
    print(f"reassigned {updated} placeholder-airline rows; {remaining} junk names remain")


if __name__ == "__main__":
    main()
