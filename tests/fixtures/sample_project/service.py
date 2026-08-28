def process(value: int) -> int:
    if value > 0:
        for item in range(value):
            if item % 2 == 0 and value > 1:
                value += item
    else:
        value = 0
    return value


def unused_helper():
    return 42
