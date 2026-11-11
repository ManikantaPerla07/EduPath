"""Editorial consistency checks for the nine Python sample resources."""

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCUMENTS = PROJECT_ROOT / "sample_documents"

TOPIC_RESOURCES = {
    "variables-data-types": "python_variables_intro_sanitized.md",
    "operators": "python_operators_expressions.md",
    "conditionals": "python_conditional_statements.md",
    "loops": "python_loops.md",
    "functions": "python_functions.md",
    "lists-tuples": "python_lists_and_tuples.md",
    "dictionaries-sets": "python_dictionaries_and_sets.md",
    "strings": "python_strings.md",
    "problem-solving": "python_basic_problem_solving.md",
}


class SampleLearningResourceTests(unittest.TestCase):

    def test_every_course_topic_has_a_sample_resource(self):
        self.assertEqual(len(TOPIC_RESOURCES), 9)

        for topic_slug, filename in TOPIC_RESOURCES.items():
            with self.subTest(topic=topic_slug):
                path = SAMPLE_DOCUMENTS / filename
                self.assertTrue(path.is_file(), f"Missing {filename}")

                content = path.read_text(encoding="utf-8-sig")
                self.assertGreater(len(content.strip()), 500)
                self.assertRegex(content, r"(?m)^# .+")
                self.assertIn("```python", content)
                self.assertRegex(
                    content,
                    r"(?m)^##\s+\d+\.\s+Practice$",
                )
                self.assertRegex(content, r"(?m)^## Key points$")

    def test_sample_resource_guide_maps_every_topic_and_file(self):
        guide = (SAMPLE_DOCUMENTS / "README.md").read_text(
            encoding="utf-8"
        )

        for topic_slug, filename in TOPIC_RESOURCES.items():
            with self.subTest(topic=topic_slug):
                self.assertIn(f"`{topic_slug}`", guide)
                self.assertIn(f"`{filename}`", guide)

    def test_sample_resources_are_markdown_only(self):
        files = {
            path.name
            for path in SAMPLE_DOCUMENTS.glob("*.md")
            if path.name != "README.md"
        }
        self.assertEqual(files, set(TOPIC_RESOURCES.values()))


if __name__ == "__main__":
    unittest.main()
