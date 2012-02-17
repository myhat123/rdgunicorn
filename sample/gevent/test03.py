import gevent
from gevent import Greenlet

def foo(message, n):
    """
    Each thread will be passed the message, and n arguments
    in its initialization.
    """
    print message
    gevent.sleep(n)

# Initialize a new Greenlet instance running the named function
# foo
thread1 = Greenlet(foo, "Hello", 1)
thread1.start()

# Wrapper for creating and runing a new Greenlet from the named 
# function foo, with the passd arguments
thread2 = gevent.spawn(foo, "I live!", 2)

# Lambda expressions
thread3 = gevent.spawn(lambda x: (x+1), 2)

threads = [thread1, thread2, thread3]

# Block until all threads complete.
gevent.joinall(threads)
