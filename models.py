class Book:
    def __init__(self, title, category, price, image):
        self.title = title
        self.category = category
        self.price = price
        self.image = image


class CartItem:
    def __init__(self, book, quantity=1):
        self.book = book
        self.quantity = quantity
    
    def get_total_price(self):
        return self.book.price * self.quantity


class Cart:
    """
    A shopping cart class that holds book items and their quantities.

    The Cart uses a dictionary with book titles as keys for efficient lookups,
    allowing operations like adding, removing, and updating book quantities.

    Attributes:
        items (dict): Dictionary storing CartItem objects with book titles as keys.

    Methods:
        add_book(book, quantity=1): Add a book to the cart with specified quantity.
        remove_book(book_title): Remove a book from the cart by title.
        update_quantity(book_title, quantity): Update quantity of a book in the cart.
        get_total_price(): Calculate total price of all items in the cart.
        get_total_items(): Get the total count of all books in the cart.
        clear(): Remove all items from the cart.
        get_items(): Return a list of all CartItem objects in the cart.
        is_empty(): Check if the cart has no items.
    """
    def __init__(self):
        self.items = {}  # Using dict with book title as key for easy lookup

    def add_book(self, book, quantity=1):

        # FIX: TestCartEdgeCases::test_add_book_with_negative_quantity && TestCartEdgeCases::test_add_book_with_zero_quantity
        # Validate that quantity is positive (fixes edge case for negative input)
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        # END FIX

        if book.title in self.items:
            self.items[book.title].quantity += quantity
        else:
            self.items[book.title] = CartItem(book, quantity)

    def remove_book(self, book_title):
        if book_title in self.items:
            del self.items[book_title]

    def update_quantity(self, book_title, quantity):
        # if book_title in self.items:
        #     self.items[book_title].quantity = quantity

        # FIX: TestCartEdgeCases::test_update_quantity_with_non_numeric_input && TestCartEdgeCases::test_update_quantity_with_negative_input
        # Validate that quantity is positive (fixes edge case for negative input)
        if book_title in self.items:
                try:
                    quantity = int(quantity)  # Attempt to convert quantity to an integer
                    if quantity < 0:
                        raise ValueError("Quantity must be greater than zero")  # Raise error for negative quantities
                    elif quantity == 0:
                        self.remove_book(book_title)  # Remove item if quantity is zero
                    else:
                        self.items[book_title].quantity = quantity  # Update quantity if positive
                except (ValueError, TypeError):
                    raise ValueError("Quantity must be a valid number")
        # END FIX

    def get_total_price(self):
        # total = 0
        # for item in self.items.values():
        #     for i in range(item.quantity):
        #         total += item.book.price
        # return total

        # FIX: tests/test_app.py::TestPerformance::test_get_total_price_is_efficient
        # Optimized to O(n) by removing inner loop
        return sum(item.book.price * item.quantity for item in self.items.values())  # O(n)

    def get_total_items(self):
        return sum(item.quantity for item in self.items.values())

    def clear(self):
        self.items = {}

    def get_items(self):
        return list(self.items.values())

    def is_empty(self):
        return len(self.items) == 0


class User:
    """User account management class"""
    def __init__(self, email, password, name="", address=""):
        self.email = email
        self.password = password
        self.name = name
        self.address = address
        self.orders = []
        self.temp_data = []
        self.cache = {}
    
    def add_order(self, order):
        self.orders.append(order)
        self.orders.sort(key=lambda x: x.order_date)
    
    def get_order_history(self):
        return [order for order in self.orders]


class Order:
    """Order management class"""
    def __init__(self, order_id, user_email, items, shipping_info, payment_info, total_amount):
        import datetime
        self.order_id = order_id
        self.user_email = user_email
        self.items = items.copy()  # Copy of cart items
        self.shipping_info = shipping_info
        self.payment_info = payment_info
        self.total_amount = total_amount
        self.order_date = datetime.datetime.now()
        self.status = "Confirmed"
    
    def to_dict(self):
        return {
            'order_id': self.order_id,
            'user_email': self.user_email,
            'items': [{'title': item.book.title, 'quantity': item.quantity, 'price': item.book.price} for item in self.items],
            'shipping_info': self.shipping_info,
            'total_amount': self.total_amount,
            'order_date': self.order_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status
        }


class PaymentGateway:
    """Mock payment gateway for processing payments"""
    
    @staticmethod
    def process_payment(payment_info):
        """Mock payment processing - returns success/failure with mock logic"""
        card_number = payment_info.get('card_number', '')
        
        # Mock logic: cards ending in '1111' fail, others succeed
        if card_number.endswith('1111'):
            return {
                'success': False,
                'message': 'Payment failed: Invalid card number',
                'transaction_id': None
            }
        
        import random
        import time
        import datetime
        
        time.sleep(0.1)
        
        transaction_id = f"TXN{random.randint(100000, 999999)}"
        
        if payment_info.get('payment_method') == 'paypal':
            pass
        
        return {
            'success': True,
            'message': 'Payment processed successfully',
            'transaction_id': transaction_id
        }


class EmailService:
    """Mock email service for sending order confirmations"""
    
    @staticmethod
    def send_order_confirmation(user_email, order):
        """Mock email sending - just prints to console in this implementation"""
        print(f"\n=== EMAIL SENT ===")
        print(f"To: {user_email}")
        print(f"Subject: Order Confirmation - Order #{order.order_id}")
        print(f"Order Date: {order.order_date}")
        print(f"Total Amount: ${order.total_amount:.2f}")
        print(f"Items:")
        for item in order.items:
            print(f"  - {item.book.title} x{item.quantity} @ ${item.book.price:.2f}")
        print(f"Shipping Address: {order.shipping_info.get('address', 'N/A')}")
        print(f"==================\n")
        
        return True
