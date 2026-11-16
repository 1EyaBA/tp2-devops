"""Logique métier du catalogue produit (sans dépendance à FastAPI, facile à tester)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: float
    stock: int


class ProductNotFoundError(Exception):
    """Le produit demandé n'existe pas."""


class OutOfStockError(Exception):
    """Stock insuffisant pour la quantité demandée."""


class InvalidQuantityError(Exception):
    """Quantité invalide (zéro, négative ou trop grande)."""


MAX_QUANTITY_PER_ITEM = 100

PRODUCTS: dict[int, Product] = {
    1: Product(1, "Clavier mécanique", 89.90, 50),
    2: Product(2, "Souris sans fil", 29.90, 120),
    3: Product(3, "Écran 27 pouces", 249.00, 15),
    4: Product(4, "Casque audio", 59.50, 0),
}


def list_products() -> list[Product]:
    return list(PRODUCTS.values())


def get_product(product_id: int) -> Product:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise ProductNotFoundError(f"Produit {product_id} introuvable")
    return product


def compute_total(items: list[tuple[int, int]]) -> float:
    """Calcule le total d'une commande [(product_id, quantity), ...].

    Règles : panier non vide, quantité entre 1 et MAX_QUANTITY_PER_ITEM,
    stock suffisant. Le total est arrondi à 2 décimales.
    """
    if not items:
        raise InvalidQuantityError("Le panier est vide")

    total = 0.0
    for product_id, quantity in items:
        if quantity <= 0 or quantity > MAX_QUANTITY_PER_ITEM:
            raise InvalidQuantityError(
                f"Quantité {quantity} invalide (1 à {MAX_QUANTITY_PER_ITEM})"
            )
        product = get_product(product_id)
        if quantity > product.stock:
            raise OutOfStockError(
                f"Stock insuffisant pour {product.name} ({product.stock} restants)"
            )
        total += product.price * quantity
    return round(total, 2)
