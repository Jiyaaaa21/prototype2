
from src.relationships import RelationshipManager


manager = RelationshipManager()

relationships = manager.get_all_relationships()

assert len(relationships) == 12

assert len(
    manager.get_relationships_by_type("DIRECT_OBSERVED")
) == 5

assert len(
    manager.get_relationships_by_type("INDIRECT_DERIVED")
) == 5

assert len(
    manager.get_relationships_by_type("BEHAVIOURAL_HYPOTHESIS")
) == 2

assert len(manager.get_component_registry()) == 6

assert len(
    manager.get_component_relationships("order_sales_management")
) == 7

print("Relationship Manager tests passed.")
print("Registered components:", len(manager.get_component_registry()))
print("Total relationships:", len(relationships))
print("Direct relationships: 5")
print("Indirect relationships: 5")
print("Behavioural hypotheses: 2")
