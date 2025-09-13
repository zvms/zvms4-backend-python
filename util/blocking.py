blocked = []

def block(item: str):
    global blocked
    blocked.append(item)

def is_blocked(item: str) -> bool:
    return item in blocked
