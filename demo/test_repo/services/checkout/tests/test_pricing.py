"""Server-side consistency test verifying cart totals."""
def calculate_server_pricing(cart_items, tax_rate=0.0825):
    subtotal = sum(item["price"] * item["qty"] for item in cart_items)
    tax = round(subtotal * tax_rate, 2)
    return subtotal + tax

def test_pricing_consistency():
    items = [{"id": "item-1", "price": 20.00, "qty": 2}]
    total = calculate_server_pricing(items)
    assert total == 43.30
