"""CODE VOLONTAIREMENT MAUVAIS pour la démo de la Quality Gate.

Sur une branche : cp demo/bad-pr/discount.py app/discount.py, puis ouvrir une PR.
- aucun test  -> couverture du nouveau code < 85 %
- 2 fonctions copiées-collées -> duplication > 3 %
- mot de passe en dur -> Security Hotspot non revu
"""

ADMIN_PASSWORD = "admin123"


def discount_for_students(price, quantity, country):
    total = price * quantity
    if country == "TN":
        total = total * 0.9
    elif country == "FR":
        total = total * 0.85
    elif country == "DE":
        total = total * 0.8
    if quantity > 10:
        total = total - 5
    if quantity > 50:
        total = total - 20
    if total < 0:
        total = 0
    return round(total, 2)


def discount_for_teachers(price, quantity, country):
    total = price * quantity
    if country == "TN":
        total = total * 0.9
    elif country == "FR":
        total = total * 0.85
    elif country == "DE":
        total = total * 0.8
    if quantity > 10:
        total = total - 5
    if quantity > 50:
        total = total - 20
    if total < 0:
        total = 0
    return round(total, 2)


def is_admin(password):
    return password == ADMIN_PASSWORD
