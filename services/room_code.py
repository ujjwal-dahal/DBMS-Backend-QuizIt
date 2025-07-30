from uuid import uuid4


def room_code_generator():
    room_code = uuid4().hex[:6]
    return room_code
