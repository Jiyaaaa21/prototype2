from src.relationships import DependencyManager


def test_initial_execution_plan():

    manager = DependencyManager()
    plan = manager.get_execution_plan()

    assert len(plan["components"]) == 6
    assert len(plan["coordination_stages"]) == 3

    assert all(
        len(dependents) == 0
        for dependents in plan["hard_dependencies"].values()
    )

    assert len(plan["execution_order"]) == 6

    assert plan["parallel_execution_batches"] == (
        (
            "customer_management",
            "product_management",
            "seller_management"
        ),
        (
            "order_sales_management",
        ),
        (
            "delivery_customer_experience",
            "payment_revenue_management"
        )
    )

    print("Initial execution plan test passed.")


def test_dependency_registration():

    manager = DependencyManager()

    manager.add_dependency(
        "customer_management",
        "order_sales_management"
    )

    dependencies = manager.get_dependencies()

    assert dependencies["customer_management"] == (
        "order_sales_management",
    )

    assert manager.validate_dependencies() is True

    print("Dependency registration test passed.")


def test_execution_batches():

    manager = DependencyManager()

    manager.add_dependency(
        "customer_management",
        "order_sales_management"
    )

    batches = manager.get_parallel_execution_batches()

    assert "customer_management" in batches[0]
    assert "order_sales_management" in batches[1]

    print("Execution batch test passed.")


def test_circular_dependency_detection():

    manager = DependencyManager()

    manager.add_dependency(
        "customer_management",
        "product_management"
    )

    try:
        manager.add_dependency(
            "product_management",
            "customer_management"
        )
    except ValueError as error:
        assert "Circular dependency" in str(error)
    else:
        raise AssertionError(
            "Circular dependency was not detected."
        )

    print("Circular dependency test passed.")


def test_invalid_component():

    manager = DependencyManager()

    try:
        manager.add_dependency(
            "invalid_component",
            "customer_management"
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Invalid component was not rejected."
        )

    print("Invalid component test passed.")


def test_stage_conflict():

    manager = DependencyManager()

    try:
        manager.add_dependency(
            "payment_revenue_management",
            "customer_management"
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Coordination stage conflict was not detected."
        )

    print("Coordination stage validation test passed.")


if __name__ == "__main__":

    test_initial_execution_plan()
    test_dependency_registration()
    test_execution_batches()
    test_circular_dependency_detection()
    test_invalid_component()
    test_stage_conflict()

    print("\nALL DEPENDENCY MANAGER TESTS PASSED.")