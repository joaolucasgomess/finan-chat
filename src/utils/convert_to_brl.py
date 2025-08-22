from decimal import Decimal


def parse_brl(value: str) -> float:
    print(value)
    cleanStr = value.replace("R$", "").strip().replace(".", "").replace(",", ".").replace(" ", "")
    print(cleanStr)
    return float(Decimal(cleanStr))
