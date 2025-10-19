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
    """Creates and-configures a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": 'test_secret_key',
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for form tests
    })
    yield flask_app

@pytest.fixture
def client(app):
    """Provides a test client for the app."""
    return app.test_client()

@pytest.fixture(autouse=True)
def setup_teardown():
    """Resets the global state before and after each test."""
    global_cart.clear()
    # Clear users added during tests to ensure isolation
    users.pop('test@example.com', None)
    users.pop('USER@test.com', None)
    users.pop('user@test.com', None)
    yield
    global_cart.clear()

# --- Integration Tests ---

def test_homepage_loads(client):
    """Test that the homepage loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Featured Books" in response.data

# def test_global_cart_bug(client):
#     """
#     This test explicitly demonstrates the CRITICAL bug where the cart is shared
#     across all user sessions.
#     """
#     # Client 1 adds an item to the cart
#     response1 = client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'}, follow_redirects=True)
#     assert b'Added 1 "1984" to cart!' in response1.data
    
#     # Create a second, independent client
#     client2 = flask_app.test_client()
    
#     # Client 2 views their cart *without* adding anything
#     response2 = client2.get('/cart')
#     assert response2.status_code == 200
    
#     # Check if Client 2's cart contains the item from Client 1
#     assert b"1984" in response2.data, "BUG CONFIRMED: Item from Client 1 appears in Client 2's cart."
#     assert not b"Your cart is empty" in response2.data, "BUG CONFIRMED: Cart should be empty for a new user."

class TestUserAuthentication:
    """Tests covering user registration and login bugs."""

    def test_user_registration_and_login_plaintext_password(self, client):
        """Tests registration and confirms the plaintext password security flaw."""
        client.post('/register', data={
            'name': 'Test User', 'email': 'test@example.com', 'password': 'password123'
        }, follow_redirects=True)
        
        assert 'test@example.com' in users
        assert users['test@example.com'].password == 'password123', "SECURITY FLAW: Password stored as plaintext."

        client.get('/logout', follow_redirects=True)
        response = client.post('/login', data={
            'email': 'test@example.com', 'password': 'password123'
        }, follow_redirects=True)
        assert b'Logged in successfully!' in response.data

    def test_invalid_login(self, client):
        """Tests login with incorrect credentials."""
        response = client.post('/login', data={'email': 'wrong@user.com', 'password': 'wrongpassword'}, follow_redirects=True)
        assert b'Invalid email or password' in response.data

    def test_register_with_invalid_email_format(self, client):
        """Tests that the system allows registration with an invalid email format."""
        response = client.post('/register', data={
            'name': 'Invalid Email User', 'email': 'not-an-email', 'password': 'password'
        }, follow_redirects=True)
        assert b'Account created successfully!' in response.data, "BUG CONFIRMED: Registration succeeded with an invalid email."

    def test_register_with_duplicate_email_different_case(self, client):
        """Tests if two users can register with the same email but different casing."""
        # Register first user with lowercase email
        client.post('/register', data={'name': 'User One', 'email': 'user@test.com', 'password': 'password123'})
        
        # Register second user with uppercase email
        response = client.post('/register', data={'name': 'User Two', 'email': 'USER@test.com', 'password': 'password456'}, follow_redirects=True)
        assert b'Account created successfully!' in response.data, "BUG CONFIRMED: Duplicate user created with different email case."

class TestCartAndCheckout:
    """Tests covering cart management and checkout bugs."""

    def test_add_to_cart_and_view(self, client):
        """Tests adding items to the cart and viewing the cart page."""
        client.post('/add-to-cart', data={'title': 'Moby Dick', 'quantity': '2'})
        response = client.get('/cart')
        assert response.status_code == 200
        assert b"Moby Dick" in response.data
        assert b'value="2"' in response.data

    # def test_add_to_cart_with_invalid_quantity(self, client):
    #     """Tests if the app crashes when a non-numeric quantity is submitted."""
    #     # This post request should ideally be handled gracefully, but in the buggy code it will cause a 500 Internal Server Error
    #     # A good test confirms this bug by checking that the server doesn't crash. We expect a 500 error here.
    #     response = client.post('/add-to-cart', data={'title': '1984', 'quantity': 'abc'})
    #     assert response.status_code == 500, "BUG CONFIRMED: App crashes on non-integer quantity input."

    def test_add_to_cart_with_invalid_quantity(self, client):
        """
        Tests that the app handles non-integer quantity input gracefully
        by flashing an error message and redirecting without crashing.
        """
        # Action: Attempt to add a book with an invalid quantity
        response = client.post('/add-to-cart', data={'title': '1984', 'quantity': 'abc'}, follow_redirects=True)

        # Assert: Check for a successful response and the error message
        assert response.status_code == 200
        assert b"Invalid quantity. Please enter a valid number." in response.data
        
        # Assert: Ensure the cart is still empty
        assert global_cart.is_empty(), "Cart should not be modified after invalid input."

    def test_update_cart_quantity_to_zero(self, client):
        """Tests if updating quantity to 0 removes the item (it shouldn't in the buggy version)."""
        client.post('/add-to-cart', data={'title': 'The Great Gatsby', 'quantity': '1'})
        client.post('/update-cart', data={'title': 'The Great Gatsby', 'quantity': '0'}, follow_redirects=True)
        
        response = client.get('/cart')
        assert b'The Great Gatsby' in response.data, "BUG CONFIRMED: Item not removed when quantity is updated to 0."
        assert b'value="0"' in response.data

    # def test_remove_from_cart(self, client):
    #     """Tests removing an item from the cart."""
    #     client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
    #     response = client.post('/remove-from-cart', data={'title': '1984'}, follow_redirects=True)
    #     assert b'Removed "1984" from cart!' in response.data
    #     assert b"1984" not in response.data

    # # NEW, CORRECTED TEST
    # def test_remove_from_cart(self, client):
    #     """
    #     Tests removing a book from the cart and verifying the flash message.
    #     """
    #     # First, add a book to the cart to ensure it's not empty
    #     client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
        
    #     # Action: Remove the book, ensuring the redirect is followed
    #     response = client.post('/remove-from-cart', data={'title': '1984'}, follow_redirects=True)

    #     # Assert: Check for a successful response and the confirmation message
    #     assert response.status_code == 200
    #     assert b'Removed "1984" from cart!' in response.data
        
    #     # Assert: Ensure the cart is now empty
    #     assert global_cart.is_empty(), "Cart should be empty after removing the item."


    def test_remove_from_cart(self, client):
        """
        Tests removing a book from the cart by manually following the redirect.
        This helps isolate errors between the POST action and the subsequent GET page load.
        """
        # Arrange: Add a book to the cart so we can remove it.
        client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
        
        # Action 1: Post to the remove-from-cart URL.
        # We expect a 302 redirect to the '/cart' page.
        # We are NOT following redirects here.
        response_post = client.post('/remove-from-cart', data={'title': '1984'})
        
        # Assert 1: Check that the server is telling us to redirect.
        assert response_post.status_code == 302, "Expected a redirect after removing an item."
        assert response_post.location == "/cart", "The redirect location should be '/cart'."

        # Action 2: Manually follow the redirect by making a GET request.
        # The flashed message from the previous request will be in the session,
        # so this request should render it.
        response_get = client.get('/cart')

        # Assert 2: Check the final page load.
        assert response_get.status_code == 200, "The cart page should load successfully after the redirect."
        assert b'Removed "1984" from your cart.' in response_get.data, "Flash message should be visible on the cart page."
        
        # Assert 3: Ensure the cart is now empty
        assert global_cart.is_empty(), "Cart should be empty after removing the item."



    # def test_checkout_with_case_sensitive_discount(self, client):
    #     """Tests if a discount code fails when entered in a different case."""
    #     client.post('/add-to-cart', data={'title': 'I Ching', 'quantity': '1'}) # Price 18.99
    #     checkout_data = {
    #         'name': 'Test User', 'email': 'test@checkout.com', 'address': '123 Lane',
    #         'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
    #         'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123',
    #         'discount_code': 'save10' # Lowercase version of 'SAVE10'
    #     }
    #     response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
    #     assert b'Invalid discount code' in response.data, "BUG CONFIRMED: Discount code is case-sensitive."

    def test_checkout_with_case_sensitive_discount(self, client):
        """
        Tests that the discount code is now case-insensitive and
        applies correctly when entered in lowercase.
        """
        # Arrange: Add a book to the cart
        client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
        
        # Action: Checkout using a lowercase discount code
        checkout_data = {
            'name': 'Test User', 'email': 'test@example.com', 'address': '123 Test St',
            'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
            'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123',
            'discount_code': 'save10'  # Use lowercase to test the fix
        }
        response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        # Assert: Check for a successful page load and the discount success message
        assert response.status_code == 200
        assert b'Discount applied! You saved' in response.data, "The discount success message should be displayed."
        assert b'Invalid discount code' not in response.data, "The invalid code message should not be displayed."

    
    def test_checkout_with_missing_payment_details(self, client):
        """Tests if checkout proceeds with empty credit card fields."""
        client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
        checkout_data = {
            'name': 'Test User', 'email': 'test@checkout.com', 'address': '123 Lane',
            'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
            'card_number': '', 'expiry_date': '', 'cvv': '' # Empty fields
        }
        response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        assert b'Please fill in all credit card details' in response.data, "BUG CONFIRMED: Validation for empty payment fields is faulty."

    # def test_checkout_flow_success(self, client):
    #     """Tests the end-to-end checkout process for a successful payment."""
    #     client.post('/add-to-cart', data={'title': 'I Ching', 'quantity': '1'})
    #     checkout_data = {
    #         'name': 'Test User', 'email': 'test@checkout.com', 'address': '123 Checkout Lane',
    #         'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
    #         'card_number': '1234 5678 9012 3456', 'expiry_date': '12/25', 'cvv': '123'
    #     }
    #     response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
    #     assert response.status_code == 200
    #     assert b'Payment successful!' in response.data
    #     assert global_cart.is_empty(), "Cart should be cleared after a successful order."

    def test_checkout_flow_success(self, client):
        """
        Tests the entire checkout flow by manually following the redirect to
        isolate any issues between the POST processing and the final GET request.
        """
        # Arrange: Add a book and get checkout data
        client.post('/add-to-cart', data={'title': '1984', 'quantity': '1'})
        checkout_data = {
            'name': 'Test User', 'email': 'test@example.com', 'address': '123 Test St',
            'city': 'Testville', 'zip_code': '12345', 'payment_method': 'credit_card',
            'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123'
        }

        # Action 1: Post to the process-checkout URL without following redirects.
        # We expect a 302 redirect response.
        response_post = client.post('/process-checkout', data=checkout_data)

        # Assert 1: Check that the server is telling us to redirect.
        assert response_post.status_code == 302, "Expected a redirect after processing payment."
        # The location header contains the URL of the confirmation page.
        redirect_location = response_post.headers['Location']
        assert '/order-confirmation/' in redirect_location, "The redirect should go to the order confirmation page."

        # Action 2: Manually follow the redirect by making a GET request to the location provided.
        response_get = client.get(redirect_location)

        # Assert 2: Check the final page load and the flash message.
        assert response_get.status_code == 200, "The order confirmation page should load successfully."
        assert b'Payment successful!' in response_get.data, "The success flash message should be visible on the confirmation page."

    def test_checkout_payment_failure(self, client):
        """Tests that the checkout process handles a failed payment correctly."""
        client.post('/add-to-cart', data={'title': 'Moby Dick', 'quantity': '1'})
        checkout_data = {
            'name': 'Fail User', 'email': 'fail@checkout.com', 'address': '404 Error Street',
            'city': 'Failburg', 'zip_code': '54321', 'payment_method': 'credit_card',
            'card_number': '0000 0000 0000 1111', 'expiry_date': '01/26', 'cvv': '999'
        }
        response = client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        assert b'Payment failed: Invalid card number' in response.data
        assert b'Checkout' in response.data
        assert not global_cart.is_empty(), "Cart should not be cleared after a failed order."

class TestPerformance:
    """
    Performance tests to identify and measure code inefficiencies.
    These tests use timeit and cProfile to gather metrics.
    """
    
    # def test_get_total_price_efficiency(self):
    #     """
    #     Measures the performance of the buggy get_total_price method.
    #     The inefficiency is a nested loop that becomes very slow with large quantities.
    #     """
    #     book = Book("Performance Test Book", "Test", 10.00, "")
    #     global_cart.add_book(book, 1000)  # Add a large quantity of one book

    #     # Use timeit to measure the execution time
    #     execution_time = timeit.timeit(lambda: global_cart.get_total_price(), number=100)
        
    #     print(f"\n[PERF] Inefficient get_total_price (1000 items) took: {execution_time:.6f}s for 100 runs.")
        
    #     # This assertion will fail on an optimized version, proving the bug.
    #     # A fast implementation would be well under 0.01s.
    #     assert execution_time > 0.01, "PERFORMANCE BUG: get_total_price is unexpectedly slow."

    def test_get_total_price_is_efficient(self, client):
        """
        Measures the performance of the get_total_price method to ensure it is efficient.
        A fast implementation should be well under 0.01s for 100 runs.
        """
        # Arrange: Add a book with a large quantity
        book = Book("Performance Test Book", "Test", 10.00, "")
        global_cart.add_book(book, 50000)

        # Action: Use timeit to measure the execution time
        execution_time = timeit.timeit(lambda: global_cart.get_total_price(), number=100)
        
        print(f"\n[PERF] Efficient get_total_price (1000 items) took: {execution_time:.6f}s for 100 runs.")
        
        # Assert: The execution time should now be very low, proving the fix.
        assert execution_time < 0.01, "PERFORMANCE REGRESSION: get_total_price is unexpectedly slow."

    def test_get_book_by_title_efficiency(self, monkeypatch):
        """
        Measures the performance of the get_book_by_title function.
        The inefficiency is iterating through a list (O(n)) instead of using a dictionary lookup (O(1)).
        """
        # Create a large list of books to demonstrate the scaling issue
        large_book_list = [Book(f"Book {i}", "Cat", 10, "") for i in range(2000)]
        last_book_title = "Book 1999"
        
        # Temporarily replace the global BOOKS list with our large list for this test
        monkeypatch.setattr('app.BOOKS', large_book_list)

        execution_time = timeit.timeit(lambda: get_book_by_title(last_book_title), number=1000)

        print(f"\n[PERF] Inefficient get_book_by_title (2000 books) took: {execution_time:.6f}s for 1000 runs.")
        assert execution_time > 0.001, "PERFORMANCE BUG: get_book_by_title is slow with many books."

    # def test_checkout_process_profiling(self, client):
    #     """
    #     Uses cProfile to analyze the entire checkout process and pinpoint bottlenecks.
    #     This test will highlight that get_total_price is the most time-consuming part.
    #     """
    #     # Set up the cart for checkout
    #     client.post('/add-to-cart', data={'title': 'I Ching', 'quantity': '50'})
    #     checkout_data = {
    #         'name': 'Profile User', 'email': 'profile@test.com', 'address': '123 Profile Lane',
    #         'city': 'Proville', 'zip_code': '54321', 'payment_method': 'credit_card',
    #         'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123'
    #     }

    #     # Create a profiler
    #     profiler = cProfile.Profile()
        
    #     # Run the checkout process under the profiler's control
    #     profiler.enable()
    #     client.post('/process-checkout', data=checkout_data, follow_redirects=True)
    #     profiler.disable()

    #     # Analyze the results
    #     stream = StringIO()
    #     stats = pstats.Stats(profiler, stream=stream).sort_stats('cumulative')
    #     stats.print_stats(10)  # Print the top 10 most time-consuming functions

    #     profile_output = stream.getvalue()
    #     print("\n[PROFILE] Checkout Process Analysis:")
    #     print(profile_output)

    #     # This assertion confirms that get_total_price is a significant part of the profile.
    #     assert 'get_total_price' in profile_output, "PROFILER WARNING: get_total_price() is a performance hotspot."

    def test_checkout_process_profiling_is_efficient(self, client):
        """
        Uses cProfile to analyze the checkout process and verify that
        get_total_price() is no longer a performance hotspot after optimization.
        """
        # Arrange: Set up the cart with a significant number of items
        client.post('/add-to-cart', data={'title': 'I Ching', 'quantity': '500'})
        checkout_data = {
            'name': 'Profile User', 'email': 'profile@test.com', 'address': '123 Profile Lane',
            'city': 'Proville', 'zip_code': '54321', 'payment_method': 'credit_card',
            'card_number': '1234567890123456', 'expiry_date': '12/25', 'cvv': '123'
        }

        # Action: Run the checkout process under the profiler
        profiler = cProfile.Profile()
        profiler.enable()
        client.post('/process-checkout', data=checkout_data, follow_redirects=True)
        profiler.disable()

        # Assert: Analyze the profiler's output
        stream = StringIO()
        # Sort by 'tottime' (total time spent in a function, excluding sub-calls)
        # to get a clear view of the biggest bottlenecks.
        stats = pstats.Stats(profiler, stream=stream).sort_stats('tottime')
        stats.print_stats(15) # Print the top 15 functions

        profile_output = stream.getvalue()
        print("\n[PROFILE] Efficient Checkout Process Analysis:")
        print(profile_output)

        # The first few lines of the output show the functions with the most self-time.
        # We assert that our optimized function is NOT in the top 5, confirming it's no longer a hotspot.
        top_functions = "\n".join(profile_output.splitlines()[5:10])
        assert 'get_total_price' not in top_functions, \
            "PROFILER OK: get_total_price() is no longer a performance hotspot."


# def test_list_all_routes(client):
#     """
#     Diagnostic test: Prints all registered routes in the application.
#     Helps debug 404 errors by showing what routes Flask is aware of.
#     """
#     import sys
#     app = client.application
#     output = []
#     for rule in app.url_map.iter_rules():
#         methods = ','.join(sorted(rule.methods))
#         output.append(f"Endpoint: {rule.endpoint:35s} Methods: {methods:30s} Rule: {str(rule)}")

#     print("\n\n--- DIAGNOSTIC: REGISTERED FLASK ROUTES ---", file=sys.stderr)
#     for line in sorted(output):
#         print(line, file=sys.stderr)
#     print("-------------------------------------------\n", file=sys.stderr)
#     assert False, "This is a diagnostic test. Check the printout above for your routes."
