import pytest
from models import Book, Cart, CartItem, User, Order

# --- Test Data Fixtures ---

@pytest.fixture
def book1():
    """Provides a sample Book object for tests."""
    return Book("The Great Gatsby", "Fiction", 10.99, "img1.jpg")

@pytest.fixture
def book2():
    """Provides another sample Book object for tests."""
    return Book("1984", "Dystopia", 8.99, "img2.jpg")

# --- Unit Tests for the Cart Class ---

class TestCart:
    """Unit tests for the Cart model."""

    def test_add_new_book(self, book1):
        """Tests adding a new book to the cart."""
        cart = Cart()
        cart.add_book(book1, 2)
        assert len(cart.items) == 1, "Cart should have one item."
        assert cart.items["The Great Gatsby"].quantity == 2, "Quantity should be 2."
        assert cart.get_total_items() == 2, "Total item count should be 2."

    def test_add_existing_book(self, book1):
        """Tests adding more of an existing book to the cart."""
        cart = Cart()
        cart.add_book(book1, 1)
        cart.add_book(book1, 3)
        assert cart.items["The Great Gatsby"].quantity == 4, "Quantity should be incremented to 4."

    def test_remove_book(self, book1, book2):
        """Tests removing a book from the cart."""
        cart = Cart()
        cart.add_book(book1)
        cart.add_book(book2, 2)
        cart.remove_book("The Great Gatsby")
        assert "The Great Gatsby" not in cart.items, "Book should be removed."
        assert "1984" in cart.items, "Other books should remain in the cart."
        assert cart.get_total_items() == 2

    def test_update_quantity(self, book1):
        """Tests updating the quantity of a book."""
        cart = Cart()
        cart.add_book(book1, 1)
        cart.update_quantity("The Great Gatsby", 5)
        assert cart.items["The Great Gatsby"].quantity == 5, "Quantity should be updated to 5."

    def test_inefficient_get_total_price(self, book1, book2):
        """
        Tests the get_total_price method to confirm its calculation.
        This test also implicitly highlights the inefficiency of the method's loop.
        """
        cart = Cart()
        cart.add_book(book1, 3)  # 3 * 10.99 = 32.97
        cart.add_book(book2, 2)  # 2 * 8.99 = 17.98
        # The expected total is 50.95. Using pytest.approx for float comparison.
        assert cart.get_total_price() == pytest.approx(50.95)

    def test_clear_cart(self, book1):
        """Tests clearing all items from the cart."""
        cart = Cart()
        cart.add_book(book1, 5)
        cart.clear()
        assert cart.is_empty(), "Cart should be empty after clearing."
        assert cart.get_total_items() == 0

# --- Unit Tests for the User Class ---

class TestUser:
    """Unit tests for the User model."""
    
    def test_user_creation(self):
        """Tests that a user is created with the correct attributes."""
        user = User("test@example.com", "password123", "Test User", "123 Test St")
        assert user.email == "test@example.com"
        assert user.password == "password123", "CRITICAL FLAW: Password stored in plaintext."
        assert user.name == "Test User"
        assert user.address == "123 Test St"
        assert len(user.orders) == 0
        assert user.temp_data == [], "Unused attribute 'temp_data' should be empty."
        assert user.cache == {}, "Unused attribute 'cache' should be empty."

    def test_add_order(self, book1):
        """Tests adding an order to a user's history."""
        user = User("test@example.com", "password123")
        order1 = Order("ORDER1", user.email, [CartItem(book1, 1)], {}, {}, 10.99)
        user.add_order(order1)
        assert len(user.orders) == 1
        assert user.orders[0].order_id == "ORDER1"
