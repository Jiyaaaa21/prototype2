import pandas as pd

from src.simulation import TimeManager


def create_test_orders():

    return pd.DataFrame({
        "order_purchase_timestamp": [
            "2017-01-05 10:30:00",
            "2017-02-15 12:00:00",
            "2017-04-20 09:00:00",
            "2017-04-25 18:00:00",
            "2017-03-10 14:00:00"
        ]
    })


def test_date_range():

    manager = TimeManager(create_test_orders())
    result = manager.get_date_range()

    assert result["start_period"] == "2017-01"
    assert result["end_period"] == "2017-04"
    assert result["total_months"] == 4

    print("Date range derivation test passed.")


def test_monthly_timeline():

    manager = TimeManager(create_test_orders())

    expected = (
        "2017-01",
        "2017-02",
        "2017-03",
        "2017-04"
    )

    assert manager.get_timeline() == expected

    print("Monthly timeline test passed.")


def test_monthly_progression():

    manager = TimeManager(create_test_orders())

    assert manager.get_current_period() == "2017-01"
    assert manager.get_next_period() == "2017-02"
    assert manager.get_next_period() == "2017-03"
    assert manager.get_next_period() == "2017-04"
    assert manager.get_next_period() is None

    print("Monthly progression test passed.")


def test_reset():

    manager = TimeManager(create_test_orders())

    manager.get_next_period()
    manager.get_next_period()

    assert manager.reset() == "2017-01"

    print("Reset test passed.")


def test_period_validation():

    manager = TimeManager(create_test_orders())

    assert manager.validate_period("2017-02") is True

    try:
        manager.validate_period("2016-12")
    except ValueError:
        pass
    else:
        raise AssertionError("Out-of-range period was accepted.")

    print("Period validation test passed.")


def test_set_current_period():

    manager = TimeManager(create_test_orders())

    assert manager.set_current_period("2017-03") == "2017-03"
    assert manager.get_next_period() == "2017-04"

    print("Set current period test passed.")


def test_invalid_timestamps():

    orders = pd.DataFrame({
        "order_purchase_timestamp": [
            "invalid",
            None
        ]
    })

    try:
        TimeManager(orders)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid timestamps were accepted.")


    print("Invalid timestamp test passed.")


def test_missing_column():

    orders = pd.DataFrame({
        "order_id": ["order_1"]
    })

    try:
        TimeManager(orders)
    except ValueError:
        pass
    else:
        raise AssertionError("Missing timestamp column was accepted.")

    print("Missing column test passed.")


if __name__ == "__main__":

    test_date_range()
    test_monthly_timeline()
    test_monthly_progression()
    test_reset()
    test_period_validation()
    test_set_current_period()
    test_invalid_timestamps()
    test_missing_column()

    print("\nALL TIME MANAGER TESTS PASSED.")