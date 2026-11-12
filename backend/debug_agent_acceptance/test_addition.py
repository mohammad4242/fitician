import unittest
from backend.debug_agent_acceptance.fixture import add

class Addition(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-2, 2), 0)
