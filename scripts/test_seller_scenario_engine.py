
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.components.seller_scenario_engine import SellerScenarioEngine


engine = SellerScenarioEngine()

# Run the five original scenarios
results = engine.run_scenarios()

print("SELLER SCENARIO RESULTS")
print("=" * 65)
print(results.round(2).to_string(index=False))

# Test business rules
print("\nBUSINESS RULE TESTS")
print("=" * 65)

rule_results = engine.get_business_rule_results()
print(rule_results.to_string(index=False))

# Test negative input rejection
print("\nINPUT VALIDATION TEST")

try:
    engine.calculate_seller_profit(
        selling_price=-100,
        cost_price=50,
        freight_collected=10,
        freight_cost=5,
        platform_commission_rate=0.10
    )
except ValueError as error:
    print("PASSED:", error)
else:
    raise AssertionError("Negative selling price was accepted.")

# Display cost disclosure
print("\nCOST DISCLOSURE")
print(engine.get_cost_disclosure())

# Final check
assert (rule_results["status"] == "PASSED").all()

print("\nALL SCENARIO ENGINE CHECKS COMPLETED.")
