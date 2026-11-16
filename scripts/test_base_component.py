
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.components.base_component import BaseComponent


# Test implementation using the abstract base class
class TestComponent(BaseComponent):

    def __init__(self):
        super().__init__("test_component")

    def run(self):
        output = {
            "component": self.component_name,
            "metadata": {},
            "historical_state": {},
            "business_metrics": {},
            "scenario_results": [],
            "business_rule_results": [],
            "status": "SUCCESS"
        }

        self.set_output(output)
        return self.get_output()


# TEST 1: Abstract class cannot be instantiated directly
try:
    BaseComponent("test")
    raise AssertionError("BaseComponent should be abstract.")
except TypeError:
    print("TEST 1 PASSED: Abstract class enforcement.")


# TEST 2: Valid component execution
component = TestComponent()
output = component.run()

assert output["component"] == "test_component"
assert output["status"] == "SUCCESS"

print("TEST 2 PASSED: Valid component execution.")


# TEST 3: Output schema validation
invalid_output = {
    "component": "test_component",
    "metadata": {}
}

try:
    component.set_output(invalid_output)
    raise AssertionError("Invalid output should be rejected.")
except ValueError:
    print("TEST 3 PASSED: Output schema validation.")


# TEST 4: Output isolation
output["metadata"]["modified"] = True

assert "modified" not in component.get_output()["metadata"]

print("TEST 4 PASSED: Output isolation.")


# TEST 5: Execution state validation
unexecuted_component = TestComponent()

try:
    unexecuted_component.get_output()
    raise AssertionError("Unexecuted component should raise an error.")
except RuntimeError:
    print("TEST 5 PASSED: Execution state validation.")


print("\nALL BASE COMPONENT TESTS PASSED.")
