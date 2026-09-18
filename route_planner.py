"""Delivery Route Planner

Reads delivery requests from a CSV file and organises them into trips that
never exceed the vehicle capacity (10 kg by default).

Usage:
    python route_planner.py samples/deliveries.csv
    python route_planner.py samples/deliveries.csv --capacity 12
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING

DEFAULT_CAPACITY = Decimal("10")
REQUIRED_COLUMNS = ["id", "area", "priority", "weight_kg"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Delivery:
    id: int
    area: str
    priority: int        # lower number = more urgent
    weight: Decimal      # kilograms (Decimal avoids float errors like 0.1 + 0.2)


@dataclass
class Trip:
    area: str
    deliveries: list

    @property
    def load(self):
        return sum((d.weight for d in self.deliveries), Decimal(0))


@dataclass
class Rejected:
    label: str           # e.g. "line 7" or "#3 (Maadi, 12 kg)"
    reason: str


def sort_key(delivery):
    """Most urgent first. Same priority -> lower ID first (so results are repeatable)."""
    return (delivery.priority, delivery.id)


# ---------------------------------------------------------------------------
# Step 1: reading and validating the input file
# ---------------------------------------------------------------------------

def parse_row(row):
    """Turn one CSV row (a dict) into a Delivery. Raises ValueError with a readable reason."""
    id_text = (row.get("id") or "").strip()
    area = " ".join((row.get("area") or "").split())     # trim + collapse extra spaces
    priority_text = (row.get("priority") or "").strip()
    weight_text = (row.get("weight_kg") or "").strip()

    try:
        delivery_id = int(id_text)
    except ValueError:
        raise ValueError(f"id '{id_text}' is not a whole number")

    if not area:
        raise ValueError("area is missing")

    try:
        priority = int(priority_text)
    except ValueError:
        raise ValueError(f"priority '{priority_text}' is not a whole number")
    if priority < 1:
        raise ValueError("priority must be 1 or higher")

    try:
        weight = Decimal(weight_text)
    except InvalidOperation:
        raise ValueError(f"weight '{weight_text}' is not a number")
    if not weight.is_finite() or weight <= 0:
        raise ValueError("weight must be a positive number")

    return Delivery(delivery_id, area, priority, weight)


def load_deliveries(path):
    """Read the CSV. Returns (valid_deliveries, rejected_rows).

    A bad row never stops the program: it is recorded in `rejected_rows`
    with a reason and the remaining rows are still processed.
    """
    deliveries = []
    rejected = []
    first_line_of_id = {}     # id -> line number, used to catch duplicate IDs

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:          # completely empty file
            return [], []

        # Be forgiving about header spelling: " ID " and "id" are the same column.
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"input file is missing column(s): {', '.join(missing)}. "
                f"Expected header: {','.join(REQUIRED_COLUMNS)}"
            )

        for row in reader:
            line = reader.line_num
            try:
                delivery = parse_row(row)
            except ValueError as error:
                rejected.append(Rejected(f"line {line}", str(error)))
                continue

            if delivery.id in first_line_of_id:
                rejected.append(Rejected(
                    f"line {line}",
                    f"duplicate id {delivery.id} (already used on line {first_line_of_id[delivery.id]})",
                ))
                continue

            first_line_of_id[delivery.id] = line
            deliveries.append(delivery)

    return deliveries, rejected


# ---------------------------------------------------------------------------
# Step 2: planning the trips
# ---------------------------------------------------------------------------

def split_by_capacity(deliveries, capacity):
    """Separate packages that can be carried from packages heavier than the vehicle."""
    ok = [d for d in deliveries if d.weight <= capacity]
    too_heavy = [d for d in deliveries if d.weight > capacity]
    return ok, too_heavy


def plan_trips(deliveries, capacity):
    """Group deliveries into trips.

    1. Put deliveries into one bucket per area (case-insensitive).
    2. Inside each area, sort by priority (most urgent first).
    3. Build trips one at a time: the most urgent remaining delivery starts the
       trip, then we go down the list and add every delivery that still fits.
       Deliveries that do not fit are kept for the next trip.
    4. Sort all trips so the trip with the most urgent delivery goes first.
    """
    for d in deliveries:
        if d.weight > capacity:
            raise ValueError(f"delivery {d.id} is heavier than the capacity; filter it out first")

    buckets = {}                      # area (lower-case) -> list of deliveries
    area_names = {}                   # area (lower-case) -> spelling to show
    for d in deliveries:
        key = d.area.casefold()
        buckets.setdefault(key, []).append(d)
        area_names.setdefault(key, d.area)

    trips = []
    for key, area_deliveries in buckets.items():
        remaining = sorted(area_deliveries, key=sort_key)
        while remaining:
            seed = remaining[0]                       # most urgent -> always fits (checked above)
            trip_items = [seed]
            load = seed.weight
            left_over = []
            for d in remaining[1:]:
                if load + d.weight <= capacity:
                    trip_items.append(d)
                    load += d.weight
                else:
                    left_over.append(d)               # would exceed capacity -> next trip
            trips.append(Trip(area_names[key], trip_items))
            remaining = left_over

    trips.sort(key=lambda t: sort_key(t.deliveries[0]))
    return trips


# ---------------------------------------------------------------------------
# Step 3: printing the result (includes the extension: efficiency summary)
# ---------------------------------------------------------------------------

def kg(value):
    """4.50 -> '4.5', 2 -> '2', 10 -> '10'."""
    return format(value.normalize(), "f")


def minimum_possible_trips(deliveries, capacity):
    """Extension: the best case, ignoring areas and priorities.
    Total weight divided by capacity, rounded up. No plan can use fewer trips."""
    total = sum((d.weight for d in deliveries), Decimal(0))
    return int((total / capacity).to_integral_value(rounding=ROUND_CEILING))


def print_report(trips, rejected, capacity):
    print(f"DELIVERY ROUTE PLAN  (vehicle capacity: {kg(capacity)} kg)")
    print("=" * 55)

    if not trips:
        print("\nNo deliveries to plan.")
    for number, trip in enumerate(trips, start=1):
        percent = trip.load / capacity * 100
        print(f"\nTrip {number} | {trip.area} | {kg(trip.load)} / {kg(capacity)} kg ({percent:.0f}% full)")
        for d in trip.deliveries:
            print(f"    #{d.id:<4} priority {d.priority}   {kg(d.weight)} kg")

    if rejected:
        print("\nNOT PLANNED (rejected)")
        print("-" * 55)
        for item in rejected:
            print(f"  {item.label}: {item.reason}")

    if trips:
        planned = [d for t in trips for d in t.deliveries]
        best_case = minimum_possible_trips(planned, capacity)
        average = sum((t.load for t in trips), Decimal(0)) / len(trips) / capacity * 100
        print("\nSUMMARY")
        print("-" * 55)
        print(f"  Deliveries planned : {len(planned)}")
        print(f"  Deliveries rejected: {len(rejected)}")
        print(f"  Trips used         : {len(trips)}")
        print(f"  Fewest trips possible (ignoring areas): {best_case}")
        print(f"  Average trip fullness: {average:.0f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan delivery trips from a CSV file.")
    parser.add_argument("input_file", help="CSV file with columns: id,area,priority,weight_kg")
    parser.add_argument("--capacity", type=Decimal, default=DEFAULT_CAPACITY,
                        help="vehicle capacity in kg (default: 10)")
    args = parser.parse_args(argv)

    if not args.capacity.is_finite() or args.capacity <= 0:
        print("Error: --capacity must be a positive number.", file=sys.stderr)
        return 1

    try:
        deliveries, rejected = load_deliveries(args.input_file)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input_file}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    plannable, too_heavy = split_by_capacity(deliveries, args.capacity)
    for d in too_heavy:
        rejected.append(Rejected(
            f"#{d.id} ({d.area}, {kg(d.weight)} kg)",
            f"heavier than the vehicle capacity of {kg(args.capacity)} kg",
        ))

    trips = plan_trips(plannable, args.capacity)
    print_report(trips, rejected, args.capacity)
    return 0


if __name__ == "__main__":
    sys.exit(main())
