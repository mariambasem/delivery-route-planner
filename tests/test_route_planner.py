import os
import random
import sys
import tempfile
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import route_planner as rp

CAP = Decimal("10")


def D(id, area, priority, weight):
    return rp.Delivery(id, area, priority, Decimal(str(weight)))


def ids(trip):
    return [d.id for d in trip.deliveries]


class PlanTripsTests(unittest.TestCase):
    def test_no_deliveries(self):
        self.assertEqual(rp.plan_trips([], CAP), [])

    def test_sample_data_from_assignment(self):
        data = [D(1, "Nasr City", 2, 4.5), D(2, "Maadi", 1, 2.0), D(3, "Nasr City", 3, 1.2),
                D(4, "Zamalek", 1, 7.0), D(5, "Maadi", 2, 3.5)]
        trips = rp.plan_trips(data, CAP)
        self.assertEqual([ids(t) for t in trips], [[2, 5], [4], [1, 3]])

    def test_exactly_at_capacity_fits(self):
        trips = rp.plan_trips([D(1, "A", 1, 6), D(2, "A", 1, 4)], CAP)
        self.assertEqual([ids(t) for t in trips], [[1, 2]])

    def test_next_package_would_exceed_capacity_goes_to_new_trip(self):
        trips = rp.plan_trips([D(1, "A", 1, 6), D(2, "A", 1, 5)], CAP)
        self.assertEqual([ids(t) for t in trips], [[1], [2]])

    def test_same_priority_is_ordered_by_id(self):
        trips = rp.plan_trips([D(3, "A", 1, 9), D(1, "A", 1, 9), D(2, "A", 1, 9)], CAP)
        self.assertEqual([ids(t) for t in trips], [[1], [2], [3]])

    def test_more_urgent_delivery_starts_earlier_trip(self):
        trips = rp.plan_trips([D(1, "A", 3, 5), D(2, "B", 1, 5)], CAP)
        self.assertEqual(ids(trips[0]), [2])

    def test_area_names_are_case_and_space_insensitive(self):
        trips = rp.plan_trips([D(1, "Maadi", 1, 1), D(2, "maadi", 1, 1)], CAP)
        self.assertEqual(len(trips), 1)

    def test_too_heavy_package_is_rejected_by_split(self):
        ok, heavy = rp.split_by_capacity([D(1, "A", 1, 10), D(2, "A", 1, "10.01")], CAP)
        self.assertEqual([d.id for d in ok], [1])
        self.assertEqual([d.id for d in heavy], [2])

    def test_plan_trips_refuses_overweight_input(self):
        with self.assertRaises(ValueError):
            rp.plan_trips([D(1, "A", 1, 11)], CAP)

    def test_decimal_weights_have_no_float_errors(self):
        # 0.1 * 100 = 10 exactly with Decimal (floats would give 9.99999...)
        data = [D(i, "A", 1, "0.1") for i in range(1, 101)]
        self.assertEqual(len(rp.plan_trips(data, CAP)), 1)

    def test_minimum_possible_trips(self):
        self.assertEqual(rp.minimum_possible_trips([D(1, "A", 1, 4.5), D(2, "B", 1, 6)], CAP), 2)
        self.assertEqual(rp.minimum_possible_trips([], CAP), 0)

    def test_random_data_keeps_the_two_hard_rules(self):
        rng = random.Random(42)
        for _ in range(200):
            n = rng.randint(0, 60)
            data = [D(i, rng.choice(["A", "B", "C"]), rng.randint(1, 4),
                      Decimal(rng.randint(1, 100)) / 10) for i in range(1, n + 1)]
            trips = rp.plan_trips(data, CAP)
            # Rule 1: no trip is over capacity
            for t in trips:
                self.assertLessEqual(t.load, CAP)
            # Rule 2: every delivery appears in exactly one trip
            planned = sorted(d.id for t in trips for d in t.deliveries)
            self.assertEqual(planned, sorted(d.id for d in data))
            # Each trip only has one area
            for t in trips:
                self.assertEqual(len({d.area for d in t.deliveries}), 1)


class LoadTests(unittest.TestCase):
    def load(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(text)
        try:
            return rp.load_deliveries(f.name)
        finally:
            os.remove(f.name)

    def test_empty_file(self):
        self.assertEqual(self.load(""), ([], []))

    def test_header_only(self):
        self.assertEqual(self.load("id,area,priority,weight_kg\n"), ([], []))

    def test_bad_rows_are_rejected_not_fatal(self):
        text = ("id,area,priority,weight_kg\n"
                "1,Maadi,1,2\n"
                "x,Maadi,1,2\n"        # bad id
                "3,,1,2\n"             # no area
                "4,Maadi,one,2\n"      # bad priority
                "5,Maadi,1,0\n"        # zero weight
                "6,Maadi,1,nan\n"      # NaN weight
                "1,Zamalek,1,2\n")     # duplicate id
        good, bad = self.load(text)
        self.assertEqual([d.id for d in good], [1])
        self.assertEqual(len(bad), 6)

    def test_missing_column_raises(self):
        with self.assertRaises(ValueError):
            self.load("id,area,priority\n1,Maadi,1\n")

    def test_header_spelling_and_bom_are_tolerated(self):
        good, bad = self.load("\ufeff ID , Area ,Priority,WEIGHT_KG\n1, Maadi ,1,2\n")
        self.assertEqual((len(good), len(bad)), (1, 0))
        self.assertEqual(good[0].area, "Maadi")


if __name__ == "__main__":
    unittest.main()
