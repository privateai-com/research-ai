"""
Demonstration of smart message handling with content change detection.

This module demonstrates how the enhanced message handling prevents
unnecessary API calls and Telegram "message is not modified" errors.
"""

from bot.messages import has_message_content_changed, get_message_content_stats


async def demonstrate_smart_messaging():
    """
    Demonstrates the benefits of smart message handling.

    This example shows how the system:
    1. Detects when message content hasn't changed
    2. Avoids unnecessary API calls to Telegram
    3. Prevents "message is not modified" errors
    """

    # Simulate a mock message for demonstration
    class MockUser:
        def __init__(self, id: int):
            self.id = id

    class MockMessage:
        def __init__(self, message_id: int, user_id: int, text: str = ""):
            self.message_id = message_id
            self.from_user = MockUser(user_id)
            self.text = text

        async def edit_text(self, text: str, **kwargs):
            """Mock edit_text that raises error for unchanged content."""
            if text == self.text:
                raise Exception("Bad Request: message is not modified")
            self.text = text
            return self

        async def answer(self, text: str, **kwargs):
            """Mock answer method."""
            return MockMessage(self.message_id + 1, self.from_user.id, text)

    # Create a mock message
    message = MockMessage(123, 456, "Initial content")

    print("=== Smart Message Handling Demo ===\n")

    # Test 1: Same content - should skip edit
    print("Test 1: Attempting to edit with same content...")
    changed = has_message_content_changed(message, "Initial content", None)  # type: ignore
    print(f"Content changed: {changed}")

    # Test 2: Different content - should allow edit
    print("\nTest 2: Attempting to edit with different content...")
    changed = has_message_content_changed(message, "Updated content", None)  # type: ignore
    print(f"Content changed: {changed}")

    # Test 3: Show memory stats
    print("\nTest 3: Memory usage statistics...")
    stats = get_message_content_stats()
    print(f"Stats: {stats}")

    print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    # Run the demonstration
    import asyncio

    asyncio.run(demonstrate_smart_messaging())
