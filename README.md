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

   file in a streaming way to lower memory use.
  

### 1. Explain your solution approach in your own words.

First, my program reads the CSV file and checks every row. If a row is wrong (for example, the area is missing or the weight is not a number), it skips that row and reports it.

Then I group the deliveries by area, and inside each area I sort them by priority (1 is the most urgent). To build a trip, I take the most urgent delivery and then add every other delivery that still fits under 10 kg. When nothing else fits, I start a new trip. At the end I sort the trips, so the trip with the most urgent delivery goes first.

I chose this approach because it is simple, and each rule in the assignment is one clear step in the code.

### 2. What was the most difficult part of the assignment?

The most difficult part was deciding what to do when the rules conflict. Grouping by area, delivering urgent packages first and using as few trips as possible cannot always all be true at the same time. In the sample data, mixing areas would need only 2 trips, but keeping areas separate needs 3. I decided to follow the rules that the assignment states (same area together, urgent first) and to only show the "fewest trips possible" number as extra information.

### 3. Are there situations where your algorithm may not produce the best possible grouping? Explain.

Yes, there are three situations:

- **Areas are never mixed.** In the sample data the total weight is 18.2 kg, so 2 trips would be possible, but my program uses 3 because each area gets its own trip.
- **Filling a trip is a simple choice, not always the best one.** For example, with weights 4, 4, 5, 6 in one area, my program makes [4,4], [5], [6], which is 3 trips. A better grouping is [4,6] and [4,5], which is only 2 trips.
- **A small, less urgent package can travel before a bigger, more urgent one.** For example, with weights 9 and 8 (both priority 1) and 1 (priority 2), the program makes [9,1] and [8]. The priority 2 package goes earlier because it fits in the empty space of the first trip. I accepted this because it uses the space better, but it means the priority order is not perfectly strict.

### 4. If the input contained 1,000,000 delivery requests, what part of your solution might become slow or memory-intensive?

The slowest part is building the trips. For every new trip, my program goes through the list of remaining deliveries again. With a very large input and many trips, this repeats many times, so the time grows very fast. In my test with 200,000 deliveries it was already slow .

The second problem is memory. The program loads all the deliveries into memory at the same time, so 1,000,000 deliveries would use a lot of memory.

### 5. What would you improve if you had another day to work on the solution?

1. Make the trip building faster, so it does not go through the whole list again for every trip.
2. Add an option to combine half-empty trips from different areas, but only for areas that are close to each other.
3. Add more tests, and an option to save the result to a file (CSV or JSON).

## Extension: efficiency summary

After the plan, the program prints how full each trip is (for example `5.5 / 10 kg (55% full)`), the average fullness, and the fewest trips that would be possible if areas were ignored (total weight divided by 10, rounded up).

I chose this because my program keeps areas separate, so it sometimes uses more trips than the minimum. This summary shows how big that difference is (in the sample data: 3 trips used, 2 possible). It is also useful for a dispatcher, because many half-empty trips cost extra time and fuel.


