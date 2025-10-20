import pytest
import timeit
import cProfile
import pstats
from io import StringIO
from app import app as flask_app, cart as global_cart, users, BOOKS, orders, get_book_by_title
from models import Book

# --- Test Setup Fixtures ---

@pytest.fixture
def app():
    """Configures a new Flask app instance for each test (Fixture for all test cases)."""
    flask_app.config.update({
        "TESTING": True,  # Enables testing mode
        "SECRET_KEY": 'test_secret_key',  # Sets a test secret key
        "WTF_CSRF_ENABLED": False,  # Disables CSRF protection for form testing
    })
    yield flask_app  # Yields the configured app for use in tests

@pytest.fixture
def client(app):
    """Creates a test client for the Flask app (Fixture for all test cases)."""
    return app.test_client()  # Returns a client to simulate HTTP requests

@pytest.fixture(autouse=True)
def setup_teardown():
    """Clears global state before and after each test to ensure test isolation (Fixture for all test cases)."""
    global_cart.clear()  # Empties the cart before test
    # Removes test users to prevent state leakage
    users.pop('test@example.com', None)
    users.pop('USER@test.com', None)
    users.pop('user@test.com', None)
    yield  # Allows the test to run
    global_cart.clear()  # Empties the cart after test

# --- Integration Tests ---

def test_homepage_loads(client):
    """
    Test Case ID: TC-BR-01
    Verifies that the homepage loads and displays books correctly (FR-001).
    Ensures the main content area shows the 'Featured Books' section.
    """
    response = client.get('/')  # Sends GET request to homepage
    assert response.status_code == 200  # Checks for successful response
    assert b"Featured Books" in response.data  # Confirms homepage content

def test_global_cart_bug(client):
    """
    Test Case ID: TC-SC-02 (extended)
    Tests for a critical bug where the cart is shared across user sessions (FR-002).
    Demonstrates unintended cart item sharing between clients, extending TC-SC-02 to test session isolation.
    """
    # Client 1 adds an item to the cart
    response1 = client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'}, follow_redirects=True)
    assert b'Added 1 "The Great Gatsby" to cart!' in response1.data  # Verifies item added
    
    # Creates a second, independent client
    client2 = flask_app.test_client()
    
    # Client 2 views their cart without adding anything
    response2 = client2.get('/cart')
    assert response2.status_code == 200  # Checks for successful cart page load
    
    # Checks if Client 2's cart contains Client 1's item
    assert b"The Great Gatsby" in response2.data, "BUG CONFIRMED: Client 1's item appears in Client 2's cart."
    assert not b"Your cart is empty" in response2.data, "BUG CONFIRMED: Cart should be empty for a new user."

class TestUserAuthentication:
    """Tests for user registration and login functionality, including security flaws."""

    def test_user_registration_and_login_plaintext_password(self, client):
        """
        Test Case ID: TC-UA-01 (User Authentication)
        Tests user registration and login, confirming plaintext password storage flaw (out of scope for FR-001/FR-002).
        Verifies successful registration and login flow.
        """
        # Registers a test user
        client.post('/register', data={
            'name': 'Test User', 'email': 'test@example.com', 'password': 'password123'
        }, follow_redirects=True)
        
        # Verifies user was added and password is stored in plaintext
        assert 'test@example.com' in users
        assert users['test@example.com'].password == 'password123', "SECURITY FLAW: Password stored as plaintext."

        client.get('/logout', follow_redirects=True)  # Logs out user
        # Attempts login with registered credentials
        response = client.post('/login', data={
            'email': 'test@example.com', 'password': 'password123'
        }, follow_redirects=True)
        assert b'Logged in successfully!' in response.data  # Confirms successful login

    def test_invalid_login(self, client):
        """
        Test Case ID: TC-UA-02 (User Authentication)
        Tests login with incorrect credentials (out of scope for FR-001/FR-002).
        Verifies appropriate error handling for invalid login attempts.
        """
        response = client.post('/login', data={'email': 'wrong@user.com', 'password': 'wrongpassword'}, follow_redirects=True)
        assert b'Invalid email or password' in response.data  # Verifies error message

    def test_register_with_invalid_email_format(self, client):
        """
        Test Case ID: TC-UA-03 (User Authentication)
        Tests registration with an invalid email format, confirming a bug (out of scope for FR-001/FR-002).
        Verifies that the system incorrectly allows invalid emails.
        """
        response = client.post('/register', data={
            'name': 'Invalid Email User', 'email': 'not-an-email', 'password': 'password'
        }, follow_redirects=True)
        assert b'Account created successfully!' in response.data, "BUG CONFIRMED: Registration succeeded with an invalid email."

    def test_register_with_duplicate_email_different_case(self, client):
        """
        Test Case ID: TC-UA-04 (User Authentication)
        Tests if duplicate emails with different casing are allowed, confirming a bug (out of scope for FR-001/FR-002).
        Verifies that the system incorrectly allows duplicate emails.
        """
        # Registers first user with lowercase email
        client.post('/register', data={'name': 'User One', 'email': 'user@test.com', 'password': 'password123'})
        
        # Registers second user with uppercase email
        response = client.post('/register', data={'name': 'User Two', 'email': 'USER@test.com', 'password': 'password456'}, follow_redirects=True)
        assert b'Account created successfully!' in response.data, "BUG CONFIRMED: Duplicate user created with different email case."

class TestCartAndCheckout:
    """Tests for cart management and checkout functionality, focusing on FR-002 and bugs."""

    def test_add_to_cart_and_view(self, client):
        """
        Test Case ID: TC-SC-01
        Verifies adding a single book to the cart and viewing the cart page (FR-002).
        Ensures the book and quantity are correctly reflected in the cart.
        """
        # client.post('/add-to-cart', data={'title': '1984', 'quantity': '2'})
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '2'}, follow_redirects=True)
        response = client.get('/cart')
        assert response.status_code == 200  # Verifies cart page loads
        # assert b"1984" in response.data  # Confirms book in cart
        assert b"The Great Gatsby" in response.data  # Confirms book in cart
        assert b'value="2"' in response.data  # Confirms quantity

    def test_add_to_cart_with_invalid_quantity(self, client):
        """
        Test Case ID: TC-SC-08
        Verifies that the app handles non-numeric quantity input gracefully (FR-002).
        Addresses DEF-001 by ensuring an error message is displayed and the cart remains unchanged.
        """
        # Attempts to add a book with invalid quantity
        response = client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': 'abc'}, follow_redirects=True)
        
        assert response.status_code == 200  # Verifies successful response
        assert b"Invalid quantity. Please enter a valid number." in response.data  # Checks for error message
        assert global_cart.is_empty(), "Cart should remain empty after invalid input."

    def test_update_cart_quantity_to_zero(self, client):
        """
        Test Case ID: TC-SC-05
        Verifies that updating a book's quantity to 0 incorrectly leaves the item in the cart (FR-002).
        Confirms a bug where the item is not removed.
        """
        client.post('/add-to-cart', data={'title': 'I Ching', 'quantity': '1'})
        client.post('/update-cart', data={'title': 'I Ching', 'quantity': '0'}, follow_redirects=True)
        
        response = client.get('/cart')
        assert b'I Ching' in response.data, "BUG CONFIRMED: Item not removed when quantity updated to 0."
        assert b'value="0"' in response.data  # Confirms zero quantity displayed

    def test_remove_from_cart(self, client):
        """
        Test Case ID: TC-SC-04
        Verifies removing a book from the cart by manually following the redirect (FR-002).
        Ensures the book is removed and a confirmation message is displayed.
        """
        # Adds a book to the cart
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'})
        
        # Sends POST request to remove book without following redirect
        response_post = client.post('/remove-from-cart', data={'title': 'The Great Gatsby'})
        
        # Verifies redirect response
        assert response_post.status_code == 302, "Expected a redirect after removing an item."
        assert response_post.location == "/cart", "Redirect should point to '/cart'."

        # Manually follows the redirect to the cart page
        response_get = client.get('/cart')
        
        # Verifies cart page and flash message
        assert response_get.status_code == 200, "Cart page should load successfully."
        assert b'Removed "The Great Gatsby" from your cart.' in response_get.data, "Flash message should confirm removal."
        assert global_cart.is_empty(), "Cart should be empty after item removal."

    def test_checkout_with_case_sensitive_discount(self, client):
        """
        Test Case ID: TC-SC-06 (extended)
        Verifies that discount codes are case-insensitive and applied correctly (FR-002).
        Tests successful discount application, extending TC-SC-06 for discount functionality.
        """
        # Adds a book to the cart
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'})
        
        # Submits checkout with lowercase discount code
        checkout_data = {
            'name': 'Test User', 'email': 'test@example.com', 'address': '123 Test St',
            'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
            'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123',
            'discount_code': 'save10'  # Tests lowercase discount code
        }
        response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        
        # Verifies successful checkout and discount application
        assert response.status_code == 200
        assert b'Discount applied! You saved' in response.data, "Discount success message should be displayed."
        assert b'Invalid discount code' not in response.data, "Invalid code message should not appear."

    def test_checkout_with_missing_payment_details(self, client):
        """
        Test Case ID: TC-SC-CH-01 (Checkout-specific)
        Verifies that checkout fails with empty credit card fields (FR-002).
        Ensures validation prevents proceeding with incomplete payment details.
        """
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'})
        checkout_data = {
            'name': 'Test User', 'email': 'test@checkout.com', 'address': '123 Lane',
            'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
            'card_number': '', 'expiry_date': '', 'cvv': ''  # Empty payment fields
        }
        response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        assert b'Please fill in all credit card details' in response.data, "BUG CONFIRMED: Validation for empty payment fields is faulty."

    def test_checkout_flow_success(self, client):
        """
        Test Case ID: TC-SC-CH-02 (Checkout-specific)
        Verifies the full checkout flow with valid payment details (FR-002).
        Tests successful payment and order confirmation by manually following redirects.
        """
        # Adds a book to the cart
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'})
        checkout_data = {
            'name': 'Test User', 'email': 'test@example.com', 'address': '123 Test St',
            'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
            'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123'
        }

        # Sends POST request to process checkout without following redirect
        response_post = client.post('/process-checkout', data=checkout_data)
        
        # Verifies redirect response
        assert response_post.status_code == 302, "Expected a redirect after processing payment."
        assert '/order-confirmation/' in response_post.headers['Location'], "Redirect should go to order confirmation page."

        # Manually follows the redirect to the confirmation page
        response_get = client.get(response_post.headers['Location'])
        
        # Verifies successful confirmation page load and message
        assert response_get.status_code == 200, "Order confirmation page should load successfully."
        assert b'Payment successful!' in response_get.data, "Success message should be displayed."

    def test_checkout_payment_failure(self, client):
        """
        Test Case ID: TC-SC-CH-03 (Checkout-specific)
        Verifies that the checkout process handles a failed payment correctly (FR-002).
        Ensures the cart remains unchanged and an error is displayed.
        """
        client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
        checkout_data = {
            'name': 'Fail User', 'email': 'fail@checkout.com', 'address': '404 Error Street',
            'city': 'Failburg', 'zip_code': '54321', 'payment_method': 'credit_card',
            'card_number': '0000 0000 0000 1111', 'expiry_date': '01/26', 'cvv': '999'
        }
        response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        assert b'Payment failed: Invalid card number' in response.data
        assert b'Checkout' in response.data
        assert not global_cart.is_empty(), "Cart should not be cleared after a failed order."

    def test_browse_books_empty_inventory(self, client, monkeypatch):
        """
        Test Case ID: TC-BR-02
        Verifies that the homepage displays an appropriate message when no books are available (FR-001).
        Addresses feedback on edge-case coverage for book browsing.
        """
        # Arrange: Temporarily empty the global BOOKS list
        monkeypatch.setattr('app.BOOKS', [])
        
        # Action: Navigate to the homepage
        response = client.get('/')
        
        # Assert: Check for successful response and empty inventory message
        assert response.status_code == 200, "Homepage should load successfully."
        assert b"No books available at this time" in response.data, "Expected message for empty inventory."
        assert b"Featured Books" not in response.data, "Featured Books section should not appear."

    def test_add_to_cart_negative_quantity(self, client):
        """
        Test Case ID: TC-SC-09
        Verifies that adding a book with a negative quantity is rejected gracefully (FR-002).
        Addresses DEF-001 and feedback on negative test coverage.
        """
        # Action: Attempt to add a book with a negative quantity
        response = client.post('/add-to-cart', data={'title': '1984', 'quantity': '-1'}, follow_redirects=True)
        
        # Assert: Check for error message and unchanged cart
        assert response.status_code == 200, "Response should be successful with an error message."
        assert b"Quantity must be positive" in response.data, "Expected error message for negative quantity."
        assert global_cart.is_empty(), "Cart should remain empty after invalid input."

    def test_update_cart_non_numeric_quantity(self, client):
        """
        Test Case ID: TC-SC-10
        Verifies that updating a cart with a non-numeric quantity is handled gracefully (FR-002).
        Addresses DEF-001, TC-SC-08, and feedback on negative test coverage.
        """
        # Arrange: Add a book to the cart
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'})
        
        # Action: Attempt to update with a non-numeric quantity
        response = client.post('/update-cart', data={'title': 'The Great Gatsby', 'quantity': 'abc'}, follow_redirects=True)
        
        # Assert: Check for error message and unchanged cart state
        assert response.status_code == 200, "Response should be successful with an error message."
        assert b"Invalid quantity. Please enter a valid number." in response.data, "Expected error message for non-numeric input."
        assert global_cart.items['The Great Gatsby'].quantity == 1, "Cart quantity should remain unchanged."
        assert b'value="1"' in response.data, "Cart page should reflect original quantity."

    def test_checkout_empty_cart(self, client):
        """
        Test Case ID: TC-SC-07
        Verifies that users cannot proceed to checkout with an empty cart (FR-002).
        Mirrors TC-SC-07 and supports integration test expansion.
        """
        # Action: Attempt to access the checkout page with an empty cart
        response = client.get('/checkout', follow_redirects=True)
        
        # Assert: Check for redirect to homepage and error message
        assert response.status_code == 200, "Should redirect to homepage."
        assert b"Your cart is empty." in response.data, "Expected empty cart error message."
        assert b"Checkout" not in response.data, "Checkout page should not be accessible."

    def test_remove_non_existent_book(self, client):
        """
        Test Case ID: TC-SC-11
        Verifies that attempting to remove a non-existent book does not affect the cart (FR-002).
        Addresses feedback on edge-case coverage.
        """
        # Arrange: Add a book to the cart
        client.post('/add-to-cart', data={'title': 'I Ching', 'quantity': '1'})
        
        # Action: Attempt to remove a non-existent book
        response = client.post('/remove-from-cart', data={'title': 'Moby Dick'}, follow_redirects=True)
        
        # Assert: Check that cart state is unchanged and no error occurs
        assert response.status_code == 200, "Response should be successful."
        assert b"I Ching" in response.data, "Existing book should remain in the cart."
        assert b"Moby Dick" not in response.data, "Non-existent book should not appear."
        assert global_cart.items['I Ching'].quantity == 1, "Cart quantity should remain unchanged."

class TestPerformance:
    """
    Performance tests to measure code efficiency using timeit and cProfile (not tied to specific TC-ID).
    Identifies and verifies fixes for performance bottlenecks.
    """
    
    def test_get_total_price_is_efficient(self, client):
        """
        Test Case ID: TC-PF-01 (Performance)
        Measures the performance of the get_total_price method to ensure efficiency (FR-002).
        Verifies that execution time is within acceptable limits for large quantities.
        """
        # Arrange: Add a book with a large quantity
        book = Book("Performance Test Book", "Test", 10.00, "")
        global_cart.add_book(book, 50000)

        # Action: Measure execution time of get_total_price
        execution_time = timeit.timeit(lambda: global_cart.get_total_price(), number=100)
        
        print(f"\n[PERF] Efficient get_total_price (50000 items) took: {execution_time:.6f}s for 100 runs.")
        
        # Assert: Verify performance is within acceptable limits
        assert execution_time < 0.01, "PERFORMANCE REGRESSION: get_total_price is unexpectedly slow."

    def test_get_book_by_title_efficiency(self, monkeypatch):
        """
        Test Case ID: TC-PF-02 (Performance)
        Measures the performance of get_book_by_title with a large book list (FR-001).
        Highlights inefficiency in list iteration (O(n)) vs. dictionary lookup (O(1)).
        """
        # Generates a large list of books
        large_book_list = [Book(f"Book {i}", "Cat", 10, "") for i in range(2000)]
        last_book_title = "Book 1999"
        
        # Temporarily replaces global BOOKS with large list
        monkeypatch.setattr('app.BOOKS', large_book_list)

        # Measures execution time for retrieving the last book
        execution_time = timeit.timeit(lambda: get_book_by_title(last_book_title), number=1000)

        print(f"\n[PERF] Inefficient get_book_by_title (2000 books) took: {execution_time:.6f}s for 1000 runs.")
        assert execution_time > 0.001, "PERFORMANCE BUG: get_book_by_title is slow with many books."

    def test_checkout_process_profiling_is_efficient(self, client):
        """
        Test Case ID: TC-PF-03 (Performance)
        Profiles the checkout process to confirm get_total_price is not a bottleneck (FR-002).
        Uses cProfile to verify performance improvements.
        """
        # Sets up cart with a large number of items
        client.post('/add-to-cart', data={'title': 'Moby Dick', 'quantity': '500'})
        checkout_data = {
            'name': 'Profile User', 'email': 'profile@test.com', 'address': '123 Profile Lane',
            'city': 'Proville', 'zip_code': '54321', 'payment_method': 'credit_card',
            'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123'
        }

        # Profiles the checkout process
        profiler = cProfile.Profile()
        profiler.enable()
        client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        profiler.disable()

        # Analyses profiler output
        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream).sort_stats('tottime')  # Sorts by time spent in functions
        stats.print_stats(15)  # Prints top 15 time-consuming functions

        profile_output = stream.getvalue()
        print("\n[PROFILE] Efficient Checkout Process Analysis:")
        print(profile_output)

        # Verifies get_total_price is not in the top 5 time-consuming functions
        top_functions = "\n".join(profile_output.splitlines()[5:10])
        assert 'get_total_price' not in top_functions, "PROFILER OK: get_total_price() is no longer a performance hotspot."

    # Compares original vs. optimised get_total_price performance
    def test_get_total_price_optimised(self, client):
        book = Book("Test", "Cat", 10.0, "")
        global_cart.add_book(book, 50000)

        # Before
        original_time = timeit.timeit(lambda: sum(item.book.price for item in global_cart.items.values() for _ in range(item.quantity)), number=100)  # Mimic original
        print(f"Original time: {original_time:.6f}s")

        # After (use optimised method)
        optimised_time = timeit.timeit(global_cart.get_total_price, number=100)
        print(f"Optimised time: {optimised_time:.6f}s")
        assert optimised_time < original_time / 10, "Optimisation should be at least 10x faster"
