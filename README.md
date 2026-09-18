# Delivery Route Planner

A small Python program that reads delivery requests from a CSV file and groups them into
trips for a vehicle that can carry at most **10 kg** per trip.

Submitted for the 2026 Software Development Internship technical assignment.

## How to run

Requirements: **Python 3.8 or newer**. No external libraries and nothing to install.

```bash
# run on the sample data
python route_planner.py samples/deliveries.csv

# run the unit tests
python -m unittest discover -s tests -v

# optional: try a different capacity
python route_planner.py samples/deliveries.csv --capacity 12
```

(On some systems the command is `python3` instead of `python`.)

### Project layout

```
route_planner.py            the whole program
samples/deliveries.csv      the 5 deliveries from the assignment
samples/edge_cases.csv      messy data: bad rows, duplicates, overweight package, ties
samples/empty.csv           header only (no deliveries)
tests/test_route_planner.py 17 unit tests
```

## Input format

A CSV file with a header row and these four columns:

| Column      | Meaning                                   | Rules                          |
|-------------|-------------------------------------------|--------------------------------|
| `id`        | Delivery ID                               | whole number, must be unique   |
| `area`      | Delivery area                             | not empty                      |
| `priority`  | Urgency, **lower number = more urgent**   | whole number, 1 or higher      |
| `weight_kg` | Package weight in kg                      | number greater than 0          |

```csv
id,area,priority,weight_kg
1,Nasr City,2,4.5
2,Maadi,1,2.0
3,Nasr City,3,1.2
4,Zamalek,1,7.0
5,Maadi,2,3.5
```

## Example output

```
DELIVERY ROUTE PLAN  (vehicle capacity: 10 kg)
=======================================================

Trip 1 | Maadi | 5.5 / 10 kg (55% full)
    #2    priority 1   2 kg
    #5    priority 2   3.5 kg

Trip 2 | Zamalek | 7 / 10 kg (70% full)
    #4    priority 1   7 kg

Trip 3 | Nasr City | 5.7 / 10 kg (57% full)
    #1    priority 2   4.5 kg
    #3    priority 3   1.2 kg

SUMMARY
-------------------------------------------------------
  Deliveries planned : 5
  Deliveries rejected: 0
  Trips used         : 3
  Fewest trips possible (ignoring areas): 2
  Average trip fullness: 61%
```

## How edge cases are handled

| Situation | What the program does | Why |
|---|---|---|
| No deliveries (empty file or header only) | Prints "No deliveries to plan." and exits normally | Nothing to do is not an error |
| Package heavier than 10 kg | Not put in any trip. Listed under "NOT PLANNED" with the reason. A package of exactly 10 kg is allowed | It can never be delivered by this vehicle, and forcing it into a trip would break the capacity rule. Silently dropping it would be worse, so it is reported |
| Same priority | Lower ID goes first | Gives the same output every time the program runs |
| Next package would exceed capacity | It is skipped for this trip and kept for the next one. Later, lighter packages may still fill the gap | Never breaks the capacity rule, and wastes less space than closing the trip immediately |
| Bad row (missing area, weight is text, weight ≤ 0, priority < 1...) | Row is rejected with its line number and reason. The other rows are still planned | One typo should not stop a whole day of deliveries |
| Duplicate ID | The first one is kept, later ones are rejected | "Every delivery appears in exactly one trip" only makes sense if IDs are unique |
| `Maadi`, `maadi`, ` Maadi  ` | Treated as the same area | These are almost certainly typing differences |
| Missing file / missing column | Clear error message and exit code 1 | |

Weights use Python's `Decimal` instead of `float`, so ten packages of 1.0 kg add up to exactly 10 kg
and not 9.999999...

## Answers to the reasoning questions

### 1. Explain your solution approach in your own words.

I read the file and check every row. Rows that are broken, duplicated or heavier than 10 kg
are set aside and reported. For the valid deliveries, I first split them into one group per area,
so trips never mix areas. Inside each area I sort by priority (1 first), and if the priority is the same, by ID.

Then I build trips one by one. The most urgent delivery that is still waiting starts a new trip.
I go down the list and add every delivery that still fits under 10 kg. The ones that don't fit stay
for the next trip. I repeat until the area is empty. At the end I sort all trips so the trip that
contains the most urgent delivery comes first.

I chose this because each rule in the assignment maps to one clear step, which makes it easy to
explain and to check.

### 2. What was the most difficult part of the assignment?

Deciding what to do when the rules pull in different directions. Grouping by area, handling urgent
deliveries first, and using as few trips as possible cannot all be satisfied at once. For example, in the
sample data mixing areas would allow 2 trips, but keeping areas separate needs 3. I decided that
area grouping and priority order are the rules the assignment states, and that "fewest trips" is only
something to measure, not a rule. Writing that decision down clearly was harder than writing the code.

### 3. Are there situations where your algorithm may not produce the best possible grouping? Explain.

Yes, in three situations:

- **Mixed areas are never combined.** In the sample data the total weight is 18.2 kg, so 2 trips would be
  possible in theory, but my plan uses 3 because Maadi, Zamalek and Nasr City each get their own trip
  with spare room. The summary line "Fewest trips possible" shows this gap.
- **Filling a trip is a greedy choice, not the perfect one.** Take one area with weights 4, 4, 5, 6 in
  priority order. My program makes `[4, 4]`, `[5]`, `[6]` = 3 trips, but `[4, 6]` and `[4, 5]` would need only
  2. This is the classic bin-packing problem, which has no known fast perfect solution.
- **A less urgent small package can travel before a more urgent heavy one.** With weights 9, 8 (both
  priority 1) and 1 (priority 2), the program makes `[9, 1]` and `[8]`. The priority-2 package is
  delivered before the second priority-1 package, because it fitted in the leftover space of trip 1.
  I accepted this on purpose: the alternative (never skipping a package) wastes a lot of capacity.
  It only ever moves a package earlier, never later, so no delivery is delayed by this.

### 4. If the input contained 1,000,000 delivery requests, what part of your solution might become slow or memory-intensive?

**Slow: building the trips.** For each new trip I scan the whole list of remaining deliveries of that area.
If there are many trips per area, the same deliveries are scanned again and again, so the time grows
roughly with the *square* of the input size. I measured it:

| Test | Result |
|---|---|
| 200,000 deliveries, 50 areas, mixed weights (about 66,000 trips) | about 15 seconds |
| 20,000 deliveries, 1 area, all heavy (6 to 9 kg, so every delivery gets its own trip) | about 23 seconds |

Because of the squared growth, 1,000,000 deliveries would take minutes in the good case and possibly hours in
the bad case. Sorting is not the problem, it is O(n log n) and fine for 1 million.

**Memory-intensive:** the program loads everything at once. Each delivery is a Python object with a
`Decimal` inside, the dictionary of area groups, the set of seen IDs and the list of trips all
exist at the same time, which is likely several hundred MB for 1 million rows. Printing 1 million lines
of report is also large.

### 5. What would you improve if you had another day to work on the solution?

1. **Fix the speed problem** by avoiding the repeated scanning. For example, keep a list of "open" trips
   per area and place each delivery directly, using a sorted structure to find a trip with enough room.
2. **Optionally combine leftover space across areas.** For example, a `--merge-areas` flag that fills
   half-empty trips with deliveries from another area. This would need a table of which areas are
   close to each other, otherwise the driver could get a very bad route.
3. **Better packing.** Try "biggest first" ordering inside each priority level, and compare the
   trip count against the theoretical minimum on random data.
4. **Output options** such as writing the plan to a JSON or CSV file, and a JSON input option.
5. **More tests** for very large files and unusual characters (Arabic area names), and process the
   file in a streaming way to lower memory use.

## Extension: efficiency summary

**What it is:** after the plan, the program prints how full each trip is (e.g. `5.5 / 10 kg (55% full)`),
the average fullness, and the **fewest trips possible** (total weight ÷ capacity, rounded up),
next to the number of trips actually used.

**Why I chose it:** the assignment says grouping may not always be the best possible. Instead of only
claiming that, the program shows how far from the best case each plan is. For the dispatcher it is useful
information (many half-empty trips means extra cost), and for me it made it easy to test the trade-off
between area grouping and the number of trips. It is small (one short function) and needs no new input data.
