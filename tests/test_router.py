import unittest
from backend.router import (
    QueryRouting,
    classify_query_local,
    calculate_predicted_cost,
    route_query
)


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.available_models = [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/mixtral-8x7b-32768",
            "groq/gemma2-9b-it",
            "deepseek/deepseek-v4-flash:free",
            "z-ai/glm-4.5-air:free",
        ]

    def test_local_classifier_technical(self):
        self.assertEqual(classify_query_local("Write a Python quicksort algorithm."), "technical/code")
        self.assertEqual(classify_query_local("How to establish a fastapi endpoint?"), "technical/code")

    def test_local_classifier_math(self):
        self.assertEqual(classify_query_local("Solve this equation: 3x + 5 = 12"), "math/logic")
        self.assertEqual(classify_query_local("Prove the Pythagorean theorem."), "math/logic")

    def test_local_classifier_ethical(self):
        self.assertEqual(classify_query_local("Is it moral to lie in order to save a life?"), "ethical/philosophical")
        self.assertEqual(classify_query_local("What is the ethical dilemma of self-driving cars?"), "ethical/philosophical")

    def test_local_classifier_creative(self):
        self.assertEqual(classify_query_local("Write a creative poem about a blue moon."), "creative")
        self.assertEqual(classify_query_local("Imagine a story of a traveler in the desert."), "creative")

    def test_local_classifier_factual_default(self):
        self.assertEqual(classify_query_local("What is the capital of France?"), "factual/research")
        self.assertEqual(classify_query_local("Who won the 1998 World Cup?"), "factual/research")
        self.assertEqual(classify_query_local("Random default sentence."), "factual/research")

    def test_calculate_predicted_cost(self):
        # 1. Council with paid Groq Llama 3.3 and Llama 3.1
        council = ["groq/llama-3.3-70b-versatile", "groq/llama-3.1-8b-instant"]
        cost = calculate_predicted_cost(council, "groq/llama-3.3-70b-versatile")
        
        # Breakdown:
        # Council models: Llama 3.3 (5000 in, 2500 out), Llama 3.1 (5000 in, 2500 out)
        # Challenger: Llama 3.1 (3500 in, 800 out)
        # Chairman: Llama 3.3 (6000 in, 1500 out)
        
        # Expected: > 0.0
        self.assertGreater(cost, 0.0)
        self.assertIsInstance(cost, float)

        # 2. Council with only free models on OpenRouter
        free_council = ["deepseek/deepseek-v4-flash:free", "z-ai/glm-4.5-air:free"]
        free_cost = calculate_predicted_cost(free_council, "deepseek/deepseek-v4-flash:free")
        self.assertEqual(free_cost, 0.0)

    def test_route_query_technical_fallback(self):
        # Test routing triggering fallback using local classifier
        # We mock query_model to fail or we let the local path take over
        import asyncio
        result = asyncio.run(route_query("Write code in Rust.", self.available_models))
        
        self.assertIsInstance(result, QueryRouting)
        self.assertEqual(result.category, "technical/code")
        self.assertTrue(result.disagreement_panel_mandatory)
        self.assertTrue(result.fact_checker_web_access)
        self.assertGreater(len(result.optimal_council), 0)
        self.assertGreater(result.estimated_cost_usd, 0.0)

    def test_route_query_creative_fallback(self):
        import asyncio
        result = asyncio.run(route_query("Write a sci-fi story.", self.available_models))
        
        self.assertEqual(result.category, "creative")
        self.assertFalse(result.disagreement_panel_mandatory)
        self.assertFalse(result.fact_checker_web_access)


if __name__ == "__main__":
    unittest.main()
