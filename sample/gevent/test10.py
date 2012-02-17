import gevent
from gevent.event import Event
a = Event()

def setter():
    """
    After 3 seconds set wake all threads waiting on the value of
    a.
    """
    gevent.sleep(3)
    a.set()

def waiter():
    """
    After 3 seconds the get call will unblock.
    """
    a.wait() # blocking
    print 'I live!'

gevent.joinall([
    gevent.spawn(setter),
    gevent.spawn(waiter),
])
