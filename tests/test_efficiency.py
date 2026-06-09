from __future__ import annotations

import unittest

from _local_package import load_local_package


load_local_package()
from omh.skill_pack import builtin_definitions, builtin_skill_templates


class EfficiencyContractTests(unittest.TestCase):
    def test_memory_schema_guidance_is_scoped_to_handoff_sensitive_skills(self) -> None:
        templates = {template.name: template.content for template in builtin_skill_templates()}
        definitions = {definition.name: definition for definition in builtin_definitions()}

        explicit_schema_skills = {
            name
            for name, content in templates.items()
            if name != "oh-my-hermes"
            and ("memory_review_card/v1" in content or "handoff_context_pack/v1" in content)
        }
        allowed_categories = {
            "delivery",
            "execution",
            "leadership",
            "maintenance",
            "monitoring",
            "optimization",
            "planning",
            "review",
            "verification",
        }

        self.assertLessEqual(len(explicit_schema_skills), 14)
        self.assertIn("ralph", explicit_schema_skills)
        self.assertIn("plan", explicit_schema_skills)
        self.assertIn("code-review", explicit_schema_skills)
        for name in explicit_schema_skills:
            self.assertIn(definitions[name].category, allowed_categories, name)

        retained_low_handoff_skills = {
            name
            for name, definition in definitions.items()
            if name != "oh-my-hermes" and definition.category not in allowed_categories
        }
        self.assertTrue(retained_low_handoff_skills)
        for name in retained_low_handoff_skills:
            self.assertNotIn("memory_review_card/v1", templates[name], name)
            self.assertNotIn("handoff_context_pack/v1", templates[name], name)
            self.assertIn("advisory local context", templates[name], name)

    def test_generated_skill_pack_keeps_memory_guidance_under_budget(self) -> None:
        combined = "\n".join(template.content for template in builtin_skill_templates())

        self.assertLessEqual(combined.count("memory_review_card/v1"), 15)
        self.assertLessEqual(combined.count("handoff_context_pack/v1"), 15)
        self.assertLessEqual(combined.count("advisory local context"), 13)


if __name__ == "__main__":
    unittest.main()
