from tests import _bootstrap  # noqa: F401

import unittest

from core.match import classify_tags, match_tag_and
from core.preset import MatchStatus, Variable, VariableValue


class MatchTests(unittest.TestCase):
    def test_match_unknown(self) -> None:
        var = Variable(
            name="Emotion",
            values=[VariableValue(name="a", tags=["tag1"])],
        )
        result = classify_tags([var], ["tag2"])
        self.assertEqual(result.variables[0].status, MatchStatus.UNKNOWN)

    def test_match_conflict(self) -> None:
        var = Variable(
            name="Emotion",
            values=[
                VariableValue(name="a", tags=["tag1"]),
                VariableValue(name="b", tags=["tag2"]),
            ],
        )
        result = classify_tags([var], ["tag1", "tag2"])
        self.assertEqual(result.variables[0].status, MatchStatus.CONFLICT)

    def test_match_tag_and(self) -> None:
        required = ["tag1", "tag2"]
        tags = ["tag1", "tag2", "tag3"]
        self.assertTrue(match_tag_and(required, tags))
        self.assertFalse(match_tag_and(required, ["tag1"]))

    def test_empty_value_tags_skip_validation(self) -> None:
        variable = Variable(
            name="Emotion",
            values=[
                VariableValue(name="a", tags=[]),
                VariableValue(name="b", tags=[]),
            ],
        )
        result = classify_tags([variable], ["tag1"])
        self.assertEqual(result.variables[0].status, MatchStatus.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
