import unittest

from pydantic import ValidationError

from core.preset import Variable, VariableValue


class SchemaTests(unittest.TestCase):
    def test_variable_validation_duplicate(self) -> None:
        with self.assertRaises(ValidationError):
            Variable(
                name="Emotion",
                values=[
                    VariableValue(name="a", tags=["tag1"]),
                    VariableValue(name="b", tags=["tag1"]),
                ],
            )

    def test_variable_validation_subset(self) -> None:
        with self.assertRaises(ValidationError):
            Variable(
                name="Emotion",
                values=[
                    VariableValue(name="a", tags=["tag1"]),
                    VariableValue(name="b", tags=["tag1", "tag2"]),
                ],
            )


if __name__ == "__main__":
    unittest.main()
