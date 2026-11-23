import pdb


def calculate_total(price, quantity):
    subtotal = price * quantity
    tax = subtotal * 0.18
    total = subtotal + tax
    return total


def main():
    pdb.set_trace()
    result = calculate_total(100, 2)
    print("Final total:", result)


if __name__ == "__main__":
    main()
