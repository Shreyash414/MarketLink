"""
Unit tests for Commodity Registry and Model Registry.
"""
import unittest
from src.config.commodity_registry import (
    CommodityConfig,
    get_commodity_config,
    list_registered_commodities,
    register_commodity_config,
)
from src.config.model_registry import (
    get_registered_model,
    load_model_registry,
    register_model,
)


class TestCommodityRegistry(unittest.TestCase):

    def test_get_onion_config(self):
        config = get_commodity_config("Onion")
        self.assertEqual(config.name, "Onion")
        self.assertEqual(config.status, "VALIDATED")
        self.assertIn("Bareilly", config.default_markets)
        self.assertIn("bareilly", config.historical_mae)
        self.assertEqual(config.historical_mae["bareilly"], 29.25)

    def test_get_new_commodities_config(self):
        for comm in ["Potato", "Tomato", "Wheat", "Rice"]:
            config = get_commodity_config(comm)
            self.assertEqual(config.name, comm)
            self.assertEqual(config.api_commodity_name, comm)
            self.assertIn(
                config.status,
                {
                    "DEVELOPMENT",
                    "VALIDATED",
                    "TESTED",
                    "INSUFFICIENT_DATA",
                    "BLOCKED_BY_DATA_ACCESS",
                    "POOR_DATA_QUALITY",
                },
            )
            self.assertTrue(len(config.default_markets) > 0)

    def test_dynamic_discovery_commodity(self):
        config = get_commodity_config("Dragonfruit")
        self.assertEqual(config.name, "Dragonfruit")
        self.assertEqual(config.status, "DISCOVERY")
        self.assertEqual(config.default_markets, [])

    def test_model_registry_lookup(self):
        onion_model = get_registered_model(commodity="Onion", market="Bareilly")
        self.assertIsNotNone(onion_model)
        self.assertGreater(onion_model["test_mae"], 0.0)


    def test_register_new_commodity_runtime(self):
        new_cfg = CommodityConfig(
            name="Garlic",
            api_commodity_name="Garlic",
            status="DEVELOPMENT",
            default_markets=["Mandsaur", "Neemuch"]
        )
        register_commodity_config(new_cfg)
        retrieved = get_commodity_config("garlic")
        self.assertEqual(retrieved.name, "Garlic")
        self.assertIn("Mandsaur", retrieved.default_markets)


if __name__ == "__main__":
    unittest.main()
