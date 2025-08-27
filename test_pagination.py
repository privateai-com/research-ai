#!/usr/bin/env python3
"""Simple test for pagination functionality."""

from bot.pagination import (
    PaginationHandler,
    TaskPaginationHandler,
    ResultsPaginationHandler,
)


def test_basic_pagination():
    """Test basic pagination functionality."""
    # Create test items
    items = [f"Item {i}" for i in range(1, 21)]

    # Create pagination handler
    pagination = PaginationHandler(items, per_page=5, title="Test Items")

    # Test first page
    text, keyboard = pagination.get_page_data(0)
    print("=== First Page ===")
    print(text)
    print(f"Keyboard buttons: {len(keyboard.inline_keyboard)}")

    # Test second page
    text, keyboard = pagination.get_page_data(1)
    print("\n=== Second Page ===")
    print(text)
    print(f"Keyboard buttons: {len(keyboard.inline_keyboard)}")

    # Test total pages
    print(f"\nTotal pages: {pagination.total_pages}")
    print(f"Total items: {len(pagination.items)}")


def test_task_pagination():
    """Test task pagination functionality."""

    # Create mock task objects
    class MockTask:
        def __init__(self, task_id, description, status):
            self.id = task_id
            self.description = description
            self.status = status

    tasks = [
        MockTask(1, "Cancer treatment research", "completed"),
        MockTask(2, "Solar energy analysis", "processing"),
        MockTask(3, "AI applications study", "queued"),
        MockTask(4, "Climate change research", "completed"),
        MockTask(5, "Quantum computing study", "failed"),
    ]

    # Create task pagination handler
    task_pagination = TaskPaginationHandler(tasks)
    text, keyboard = task_pagination.get_page_data(0)

    print("=== Task Pagination ===")
    print(text)
    print(f"Task buttons: {len(keyboard.inline_keyboard)}")


def test_results_pagination():
    """Test results pagination functionality."""

    # Create mock analysis and paper objects
    class MockAnalysis:
        def __init__(self, relevance):
            self.relevance = relevance

    class MockPaper:
        def __init__(self, title):
            self.title = title

    results = [
        (MockAnalysis(95.5), MockPaper("Novel Cancer Treatment Approaches")),
        (MockAnalysis(87.2), MockPaper("Solar Energy Efficiency Improvements")),
        (MockAnalysis(92.1), MockPaper("AI in Medical Diagnosis")),
        (MockAnalysis(78.9), MockPaper("Climate Change Impact Analysis")),
        (MockAnalysis(85.3), MockPaper("Quantum Computing Applications")),
    ]

    # Create results pagination handler
    results_pagination = ResultsPaginationHandler(results)
    text, keyboard = results_pagination.get_page_data(0)

    print("=== Results Pagination ===")
    print(text)
    print(f"Result buttons: {len(keyboard.inline_keyboard)}")


if __name__ == "__main__":
    print("Testing Pagination Functionality\n")

    test_basic_pagination()
    print("\n" + "=" * 50 + "\n")

    test_task_pagination()
    print("\n" + "=" * 50 + "\n")

    test_results_pagination()

    print("\n✅ All pagination tests completed!")
