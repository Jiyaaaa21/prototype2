
from dataclasses import dataclass
from typing import Literal


RelationshipType = Literal[
    "DIRECT_OBSERVED",
    "INDIRECT_DERIVED",
    "BEHAVIOURAL_HYPOTHESIS"
]


@dataclass(frozen=True)
class ComponentRelationship:
    """
    Represents a relationship between two business components.

    A relationship does not automatically imply an execution dependency.
    """

    source: str
    target: str
    relationship_type: RelationshipType
    mechanism: str
    execution_dependency: bool = False


class RelationshipManager:
    """
    Maintains the relationship registry for the
    Commercial & Sales Digital Twin.
    """

    COMPONENTS = {
        "customer_management",
        "product_management",
        "seller_management",
        "order_sales_management",
        "payment_revenue_management",
        "delivery_customer_experience"
    }

    def __init__(self):

        self._relationships = self._register_relationships()

    def _register_relationships(self):
        """
        Register observed, derived and hypothetical
        relationships between business components.
        """

        return (

            # Direct / observed relationships

            ComponentRelationship(
                source="customer_management",
                target="order_sales_management",
                relationship_type="DIRECT_OBSERVED",
                mechanism="customer_id links customer records to orders."
            ),

            ComponentRelationship(
                source="product_management",
                target="order_sales_management",
                relationship_type="DIRECT_OBSERVED",
                mechanism="product_id links products to order items."
            ),

            ComponentRelationship(
                source="seller_management",
                target="order_sales_management",
                relationship_type="DIRECT_OBSERVED",
                mechanism="seller_id links sellers to order items."
            ),

            ComponentRelationship(
                source="order_sales_management",
                target="payment_revenue_management",
                relationship_type="DIRECT_OBSERVED",
                mechanism="order_id links orders to payment records."
            ),

            ComponentRelationship(
                source="order_sales_management",
                target="delivery_customer_experience",
                relationship_type="DIRECT_OBSERVED",
                mechanism="order_id links order timestamps and reviews."
            ),

            # Indirect / derived relationships

            ComponentRelationship(
                source="product_management",
                target="payment_revenue_management",
                relationship_type="INDIRECT_DERIVED",
                mechanism=(
                    "Product-level attribution of payment values "
                    "through order items and orders."
                )
            ),

            ComponentRelationship(
                source="seller_management",
                target="payment_revenue_management",
                relationship_type="INDIRECT_DERIVED",
                mechanism=(
                    "Seller-level attribution of payment values "
                    "through order items and orders."
                )
            ),

            ComponentRelationship(
                source="seller_management",
                target="delivery_customer_experience",
                relationship_type="INDIRECT_DERIVED",
                mechanism=(
                    "Seller item lines can be linked to order "
                    "delivery timestamps and reviews."
                )
            ),

            ComponentRelationship(
                source="delivery_customer_experience",
                target="customer_management",
                relationship_type="INDIRECT_DERIVED",
                mechanism=(
                    "Delivery and review history can be aggregated "
                    "using customer identity."
                )
            ),

            ComponentRelationship(
                source="customer_management",
                target="product_management",
                relationship_type="INDIRECT_DERIVED",
                mechanism=(
                    "Customer purchase history can be aggregated "
                    "by product and category."
                )
            ),

            # Behavioural hypotheses

            ComponentRelationship(
                source="delivery_customer_experience",
                target="order_sales_management",
                relationship_type="BEHAVIOURAL_HYPOTHESIS",
                mechanism=(
                    "Delivery experience may influence future ordering; "
                    "this effect requires empirical validation."
                )
            ),

            ComponentRelationship(
                source="customer_management",
                target="order_sales_management",
                relationship_type="BEHAVIOURAL_HYPOTHESIS",
                mechanism=(
                    "Historical purchase and satisfaction patterns "
                    "may help predict future purchasing."
                )
            )
        )

    def get_all_relationships(self):
        """Return all registered component relationships."""

        return self._relationships

    def get_relationships_by_type(self, relationship_type):
        """Return relationships matching a specified type."""

        return tuple(
            relationship
            for relationship in self._relationships
            if relationship.relationship_type == relationship_type
        )

    def get_component_relationships(self, component_name):
        """Return all relationships involving a component."""

        if component_name not in self.COMPONENTS:
            raise ValueError(
                f"Unknown component: {component_name}"
            )

        return tuple(
            relationship
            for relationship in self._relationships
            if (
                relationship.source == component_name
                or relationship.target == component_name
            )
        )

    def get_component_registry(self):
        """Return the registered component identifiers."""

        return tuple(sorted(self.COMPONENTS))
