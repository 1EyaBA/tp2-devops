import pytest

from app import catalog


def test_list_products_returns_all():
    products = catalog.list_products()
    assert len(products) == 4
    assert products[0].name == "Clavier mécanique"


def test_get_product_ok():
    assert catalog.get_product(2).price == 29.90


def test_get_product_not_found():
    with pytest.raises(catalog.ProductNotFoundError):
        catalog.get_product(999)


def test_compute_total_single_item():
    assert catalog.compute_total([(1, 2)]) == 179.80


def test_compute_total_multiple_items_rounded():
    # 29.90 * 3 + 249.00 = 338.70
    assert catalog.compute_total([(2, 3), (3, 1)]) == 338.70


def test_compute_total_empty_cart():
    with pytest.raises(catalog.InvalidQuantityError):
        catalog.compute_total([])


@pytest.mark.parametrize("quantity", [0, -1, catalog.MAX_QUANTITY_PER_ITEM + 1])
def test_compute_total_invalid_quantity(quantity):
    with pytest.raises(catalog.InvalidQuantityError):
        catalog.compute_total([(1, quantity)])


def test_compute_total_max_quantity_boundary():
    # 100 souris en stock (120) : la limite haute est acceptée
    assert catalog.compute_total([(2, catalog.MAX_QUANTITY_PER_ITEM)]) == 2990.0


def test_compute_total_out_of_stock():
    with pytest.raises(catalog.OutOfStockError):
        catalog.compute_total([(4, 1)])  # casque : stock 0


def test_compute_total_exact_stock_is_ok():
    assert catalog.compute_total([(3, 15)]) == 3735.0


def test_compute_total_unknown_product():
    with pytest.raises(catalog.ProductNotFoundError):
        catalog.compute_total([(42, 1)])
