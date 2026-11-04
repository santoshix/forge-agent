"""Hand-authored benchmark fixtures. Demo proposals are scripted, never LLM claims."""

CASES = {
    "average": {
        "title": "Handle an empty average",
        "issue": "average([]) must return 0. Preserve the arithmetic mean for nonempty lists.",
        "before": "def average(values):\n    return sum(values) / len(values)\n",
        "after": "def average(values):\n    if not values:\n        return 0\n    return sum(values) / len(values)\n",
        "tests": "from src.logic import average\nimport unittest\nclass Cases(unittest.TestCase):\n    def test_empty(self): self.assertEqual(average([]), 0)\n    def test_mean(self): self.assertEqual(average([2,4,6]), 4)\n    def test_negative(self): self.assertEqual(average([-2,-4]), -3)\n",
    },
    "discount": {
        "title": "Correct percentage discounts",
        "issue": "discount(price, percent) must subtract a percentage of the price, not a fixed amount.",
        "before": "def discount(price, percent):\n    return price - percent\n",
        "after": "def discount(price, percent):\n    return price * (1 - percent / 100)\n",
        "tests": "from src.logic import discount\nimport unittest\nclass Cases(unittest.TestCase):\n    def test_percent(self): self.assertEqual(discount(200,10), 180)\n    def test_zero(self): self.assertEqual(discount(30,0), 30)\n    def test_full(self): self.assertEqual(discount(25,100), 0)\n",
    },
    "unique": {
        "title": "Preserve order when deduplicating",
        "issue": "unique(values) must preserve first occurrence order and remove duplicates. Inputs are hashable.",
        "before": "def unique(values):\n    return sorted(set(values))\n",
        "after": "def unique(values):\n    return list(dict.fromkeys(values))\n",
        "tests": 'from src.logic import unique\nimport unittest\nclass Cases(unittest.TestCase):\n    def test_order(self): self.assertEqual(unique([3,1,3,2]), [3,1,2])\n    def test_empty(self): self.assertEqual(unique([]), [])\n    def test_words(self): self.assertEqual(unique(["z","a","z"]), ["z","a"])\n',
    },
}


def files(case):
    c = CASES[case]
    return {
        "src/__init__.py": "",
        "src/logic.py": c["before"],
        "tests/test_logic.py": c["tests"],
    }
