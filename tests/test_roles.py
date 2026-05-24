import unittest
from backend.roles import allocate_roles, RoleAssignment


class TestRolesAllocation(unittest.TestCase):
    def setUp(self):
        self.models = [
            "modelA",
            "modelB",
            "modelC",
            "modelD",
            "modelE",
            "modelF"
        ]

    def test_allocate_empty_list_raises(self):
        with self.assertRaises(ValueError):
            allocate_roles([], "technical")

    def test_allocate_invalid_query_type_falls_back(self):
        # Invalid query type 'unknown' should fallback to 'factual'
        assignment = allocate_roles(self.models, "unknown", query_index=0)
        self.assertEqual(assignment.chairman, "modelA")
        # Factual chairman template check
        self.assertIn("fact-finding committee", assignment.system_prompts["modelA"])

    def test_allocate_dataclass_fields(self):
        assignment = allocate_roles(self.models, "technical", query_index=0)
        self.assertIsInstance(assignment, RoleAssignment)
        self.assertEqual(assignment.chairman, "modelA")
        self.assertEqual(assignment.devils_advocate, "modelB")
        self.assertEqual(assignment.fact_checker, "modelC")
        self.assertEqual(assignment.steelmanner, "modelD")
        self.assertEqual(assignment.reasoners, ["modelE", "modelF"])

    def test_role_rotation(self):
        # query_index = 1: shift of 1 (modelB is first)
        assignment_1 = allocate_roles(self.models, "technical", query_index=1)
        self.assertEqual(assignment_1.chairman, "modelB")
        self.assertEqual(assignment_1.devils_advocate, "modelC")
        self.assertEqual(assignment_1.reasoners, ["modelF", "modelA"])

        # query_index = 2: shift of 2 (modelC is first)
        assignment_2 = allocate_roles(self.models, "technical", query_index=2)
        self.assertEqual(assignment_2.chairman, "modelC")
        self.assertEqual(assignment_2.devils_advocate, "modelD")

        # query_index = 6: shift of 6 % 6 = 0 (modelA is first again)
        assignment_6 = allocate_roles(self.models, "technical", query_index=6)
        self.assertEqual(assignment_6.chairman, "modelA")

    def test_graceful_degradation_fewer_models(self):
        # 1 model fallback
        assignment_1 = allocate_roles(["modelA"], "technical", query_index=0)
        self.assertEqual(assignment_1.chairman, "modelA")
        self.assertEqual(assignment_1.devils_advocate, "")
        self.assertEqual(assignment_1.reasoners, [])
        self.assertEqual(len(assignment_1.system_prompts), 1)

        # 2 models fallback
        assignment_2 = allocate_roles(["modelA", "modelB"], "technical", query_index=0)
        self.assertEqual(assignment_2.chairman, "modelA")
        self.assertEqual(assignment_2.devils_advocate, "modelB")
        self.assertEqual(assignment_2.reasoners, [])
        self.assertEqual(len(assignment_2.system_prompts), 2)

        # 3 models fallback
        assignment_3 = allocate_roles(["modelA", "modelB", "modelC"], "technical", query_index=0)
        self.assertEqual(assignment_3.chairman, "modelA")
        self.assertEqual(assignment_3.devils_advocate, "modelB")
        self.assertEqual(assignment_3.reasoners, ["modelC"])
        self.assertEqual(len(assignment_3.system_prompts), 3)

        # 4 models fallback
        assignment_4 = allocate_roles(["modelA", "modelB", "modelC", "modelD"], "technical", query_index=0)
        self.assertEqual(assignment_4.chairman, "modelA")
        self.assertEqual(assignment_4.devils_advocate, "modelB")
        self.assertEqual(assignment_4.reasoners, ["modelC"])
        self.assertEqual(assignment_4.fact_checker, "modelD")
        self.assertEqual(assignment_4.steelmanner, "")
        self.assertEqual(len(assignment_4.system_prompts), 4)

    def test_customized_prompts_by_query_type(self):
        types = ["technical", "creative", "factual", "ethical", "math"]
        keywords = {
            "technical": "technical engineering",
            "creative": "creative writing",
            "factual": "fact-finding committee",
            "ethical": "ethical debate",
            "math": "mathematical proofs"
        }
        for qt in types:
            assignment = allocate_roles(self.models, qt, query_index=0)
            chairman_prompt = assignment.system_prompts["modelA"]
            self.assertIn(keywords[qt], chairman_prompt)


if __name__ == "__main__":
    unittest.main()
