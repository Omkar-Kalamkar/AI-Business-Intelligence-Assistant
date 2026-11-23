import insight_history


def test_save_and_get_roundtrip():
    payload = {"summary": {"total_sales": 1234.5}, "items": [1, 2, 3]}

    saved = insight_history.save_insight(
        filename="sales.csv",
        payload=payload,
        kind="business_insights",
        dataset_hash="abc123",
        record_count=42,
    )

    assert saved["id"] > 0
    assert saved["created_at"]
    assert saved["filename"] == "sales.csv"
    assert saved["dataset_hash"] == "abc123"
    assert saved["record_count"] == 42

    fetched = insight_history.get_insight(saved["id"])
    assert fetched["payload"] == payload
    assert fetched["kind"] == "business_insights"


def test_list_orders_newest_first_with_pagination():
    for index in range(5):
        insight_history.save_insight(
            filename=f"file_{index}.csv",
            payload={"index": index},
        )

    page = insight_history.list_insights(limit=2, offset=0)
    assert page["total"] == 5
    assert len(page["items"]) == 2
    assert page["items"][0]["filename"] == "file_4.csv"

    page_two = insight_history.list_insights(limit=2, offset=2)
    assert page_two["items"][0]["filename"] == "file_2.csv"


def test_delete():
    saved = insight_history.save_insight(
        filename="gone.csv", payload={}
    )

    assert insight_history.delete_insight(saved["id"]) is True
    assert insight_history.get_insight(saved["id"]) is None
    assert insight_history.delete_insight(saved["id"]) is False


def test_get_missing_returns_none():
    assert insight_history.get_insight(99999) is None
