import unittest

from src.extractors import extract_education, extract_experience, extract_role, extract_skills


class ExtractorTests(unittest.TestCase):
    def test_extracts_sample_description(self):
        description = (
            "We are looking for a Full Stack Developer with Java, Spring Boot, "
            "React and MySQL experience. Experience: 2-4 years. B.Tech preferred."
        )
        taxonomy = {
            "Programming": ["Java"],
            "Database": ["MySQL"],
            "Framework": ["Spring Boot", "React"],
        }
        self.assertEqual(extract_role(description), "Full Stack Developer")
        self.assertEqual(extract_experience(description), "2-4 years")
        self.assertEqual(extract_education(description), "B.Tech")
        self.assertEqual(
            extract_skills(description, taxonomy),
            {"Programming": ["Java"], "Database": ["MySQL"], "Framework": ["Spring Boot", "React"]},
        )

    def test_skill_boundaries_prevent_partial_matches(self):
        self.assertEqual(extract_skills("Experience with a reliable team.", {"Programming": ["R"]}), {})

    def test_title_is_used_when_description_has_no_known_role(self):
        self.assertEqual(extract_role("Build internal tools.", "Platform Specialist"), "Platform Specialist")


if __name__ == "__main__":
    unittest.main()
