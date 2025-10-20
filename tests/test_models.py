import pytest
from models import Book, Cart, CartItem, User, Order, PaymentGateway, EmailService

# --- Test Data Fixtures ---

@pytest.fixture
def book1():
    """Creates a sample Book object for tests (Fixture for all test cases)."""
    return Book("Cry, the Beloved Country", "Fiction", 10.99, "img1.jpg")  # Alan Paton's classic novel

@pytest.fixture
def book2():
    """Creates another sample Book object for tests (Fixture for all test cases)."""
    return Book("The Power of One", "Historical Fiction", 8.99, "img2.jpg")  # Bryce Courtenay's novel

# --- Unit Tests for the Cart Class ---

class TestCart:
    """Unit tests for the Cart model, verifying cart-related functionality (FR-002)."""

    def test_add_new_book(self, book1):
        """
        Test Case ID: TC-MD-01
        Verifies adding a new book to an empty cart (FR-002).
        Ensures the cart correctly tracks the book and quantity.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 2)  # Adds 2 copies of the book
        assert len(cart.items) == 1, "Cart should contain exactly one item."
        assert cart.items["Cry, the Beloved Country"].quantity == 2, "Quantity should be set to 2."
        assert cart.get_total_items() == 2, "Total item count should reflect 2 items."

    def test_add_existing_book(self, book1):
        """
        Test Case ID: TC-MD-02
        Verifies adding more copies of an existing book increments the quantity (FR-002).
        Ensures the cart consolidates quantities for the same book.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 1)  # Adds 1 copy of the book
        cart.add_book(book1, 3)  # Adds 3 more copies of the same book
        assert cart.items["Cry, the Beloved Country"].quantity == 4, "Quantity should be incremented to 4."

    def test_remove_book(self, book1, book2):
        """
        Test Case ID: TC-MD-03
        Verifies removing a book from the cart while keeping others (FR-002).
        Ensures only the specified book is removed.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1)  # Adds first book with default quantity (1)
        cart.add_book(book2, 2)  # Adds second book with quantity 2
        cart.remove_book("Cry, the Beloved Country")  # Removes the first book
        assert "Cry, the Beloved Country" not in cart.items, "Book should be removed from the cart."
        assert "The Power of One" in cart.items, "Other books should remain in the cart."
        assert cart.get_total_items() == 2, "Total item count should reflect remaining items."

    def test_update_quantity(self, book1):
        """
        Test Case ID: TC-MD-04
        Verifies updating the quantity of a book in the cart (FR-002).
        Ensures the quantity is correctly updated.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 1)  # Adds 1 copy of the book
        cart.update_quantity("Cry, the Beloved Country", 5)  # Updates quantity to 5
        assert cart.items["Cry, the Beloved Country"].quantity == 5, "Quantity should be updated to 5."

    def test_inefficient_get_total_price(self, book1, book2):
        """
        Test Case ID: TC-MD-05
        Verifies the get_total_price method calculates the correct total (FR-002).
        Highlights potential inefficiency in the method's implementation.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 3)  # Adds 3 copies of first book (3 * $10.99 = $32.97)
        cart.add_book(book2, 2)  # Adds 2 copies of second book (2 * $8.99 = $17.98)
        # Expected total: $32.97 + $17.98 = $50.95
        assert cart.get_total_price() == pytest.approx(50.95), "Total price should be approximately $50.95."

    def test_clear_cart(self, book1):
        """
        Test Case ID: TC-MD-06
        Verifies that clearing the cart removes all items (FR-002).
        Ensures the cart is empty and item count is zero.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 5)  # Adds 5 copies of the book
        cart.clear()  # Clears the cart
        assert cart.is_empty(), "Cart should be empty after clearing."
        assert cart.get_total_items() == 0, "Total item count should be 0 after clearing."

class TestUser:
    """Unit tests for the User model, verifying user creation and order management (out of scope for FR-001/FR-002)."""

    def test_user_creation(self):
        """
        Test Case ID: TC-MD-07
        Verifies that a user is created with the correct attributes (out of scope for FR-001/FR-002).
        Confirms plaintext password storage flaw and correct attribute initialization.
        """
        user = User("test@example.com", "password123", "Test User", "123 Test St")  # Creates a new user with all attributes
        assert user.email == "test@example.com", "Email should match input."
        assert user.password == "password123", "CRITICAL FLAW: Password stored in plaintext."
        assert user.name == "Test User", "Name should match input."
        assert user.address == "123 Test St", "Address should match input."
        assert len(user.orders) == 0, "New user should have no orders."
        assert user.temp_data == [], "Unused 'temp_data' attribute should be empty."
        assert user.cache == {}, "Unused 'cache' attribute should be empty."

    def test_add_order(self, book1):
        """
        Test Case ID: TC-MD-08
        Verifies adding an order to a user's order history (out of scope for FR-001/FR-002).
        Ensures the order is correctly added to the user's history.
        """
        user = User("test@example.com", "password123")  # Creates a new user
        order1 = Order("ORDER1", user.email, [CartItem(book1, 1)], {}, {}, 10.99)  # Creates a sample order
        user.add_order(order1)  # Adds the order to the user's history
        assert len(user.orders) == 1, "User should have exactly one order."
        assert user.orders[0].order_id == "ORDER1", "Order ID should match 'ORDER1'."

class TestPaymentGateway:
    def test_process_success(self):
        info = {'payment_method': 'credit_card', 'card_number': '1234567890123456'}
        result = PaymentGateway.process_payment(info)
        assert result['success']
        assert 'TXN' in result['transaction_id']

    def test_process_failure(self):
        info = {'payment_method': 'credit_card', 'card_number': '1234567890121111'}
        result = PaymentGateway.process_payment(info)
        assert not result['success']
        assert 'Invalid card number' in result['message']

class TestEmailService:
    def test_send_confirmation(self, capsys):  # Capture print output
        order = Order("123", "test@email.com", [], {}, {}, 10.0)
        EmailService.send_order_confirmation("test@email.com", order)
        captured = capsys.readouterr()
        assert "EMAIL SENT" in captured.out
        assert "Order #123" in captured.out

class TestCartEdgeCases:
    """Unit tests for edge and negative cases in the Cart model, ensuring robust backend validation (FR-002)."""

    def test_add_book_with_negative_quantity(self, book1):
        """
        Test Case ID: TC-MD-09
        Verifies that adding a book with a negative quantity is rejected (FR-002).
        Addresses DEF-001 and feedback on negative test case coverage.
        """
        cart = Cart()  # Initialises a new empty cart
        with pytest.raises(ValueError, match="Quantity must be greater than zero"):  # Expects a ValueError
            cart.add_book(book1, -1)  # Attempts to add a negative quantity
        assert cart.is_empty(), "Cart should remain empty after invalid input."
        assert len(cart.items) == 0, "No items should be added to the cart."

    def test_add_book_with_zero_quantity(self, book1):
        """
        Test Case ID: TC-MD-10
        Verifies that adding a book with zero quantity is rejected (FR-002).
        Ensures backend robustness as per TC-SC-05 feedback.
        """
        cart = Cart()  # Initialises a new empty cart
        with pytest.raises(ValueError, match="Quantity must be greater than zero"):  # Expects a ValueError
            cart.add_book(book1, 0)  # Attempts to add zero quantity
        assert cart.is_empty(), "Cart should remain empty after invalid input."
        assert len(cart.items) == 0, "No items should be added to the cart."

    def test_update_quantity_with_non_numeric_input(self, book1):
        """
        Test Case ID: TC-MD-11
        Verifies that updating a book's quantity with a non-numeric value is handled gracefully (FR-002).
        Addresses DEF-001 and feedback on negative testing.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 1)  # Adds 1 copy of the book
        with pytest.raises(ValueError, match="Quantity must be a valid number"):  # Expects a ValueError
            cart.update_quantity("Cry, the Beloved Country", "abc")  # Attempts non-numeric input
        assert cart.items["Cry, the Beloved Country"].quantity == 1, "Quantity should remain unchanged."
        assert cart.get_total_items() == 1, "Total item count should remain unchanged."

    def test_update_quantity_with_negative_input(self, book1):
        """
        Test Case ID: TC-MD-12
        Verifies that updating a book's quantity to a negative value is rejected (FR-002).
        Ensures backend validation and addresses negative test case feedback.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 1)  # Adds 1 copy of the book
        with pytest.raises(ValueError, match="Quantity must be greater than zero"):  # Expects a ValueError
            cart.update_quantity("Cry, the Beloved Country", -1)  # Attempts negative quantity
        assert cart.items["Cry, the Beloved Country"].quantity == 1, "Quantity should remain unchanged."
        assert cart.get_total_items() == 1, "Total item count should remain unchanged."

    def test_remove_non_existent_book(self, book1):
        """
        Test Case ID: TC-MD-13
        Verifies that attempting to remove a non-existent book does not affect the cart (FR-002).
        Tests edge case to ensure robustness.
        """
        cart = Cart()  # Initialises a new empty cart
        cart.add_book(book1, 1)  # Adds 1 copy of the book
        cart.remove_book("The Power of One")  # Attempts to remove a book not in the cart
        assert "Cry, the Beloved Country" in cart.items, "Existing book should remain in the cart."
        assert "The Power of One" not in cart.items, "Non-existent book should not be added."
        assert cart.get_total_items() == 1, "Total item count should remain unchanged."
