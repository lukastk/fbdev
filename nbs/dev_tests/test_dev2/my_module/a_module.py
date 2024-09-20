has_been_called = False

def foo():
    global has_been_called
    print("Hello world again")
    has_been_called = True