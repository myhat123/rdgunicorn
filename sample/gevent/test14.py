import gevent
from gevent import Greenlet
from gevent import queue

class Actor(gevent.Greenlet):

    def __init__(self):
        self.inbox = queue.Queue()
        Greenlet.__init__(self)

    def recieve(self, message):
        """
        Define in your subclass.
        """
        raise NotImplemented()

    def _run(self):
        self.running = True

        while self.running:
            message = self.inbox.get()
            self.recieve(message)


class Echo(Actor):
    def recieve(self, message):
        print message

class Speaker(Actor):
    def recieve(self, message):
        if message == 'start':
            for i in xrange(1,5):
                echo.inbox.put('Hey there!')

echo = Echo()
speak = Speaker()

echo.start()
speak.start()

speak.inbox.put('start')
gevent.joinall([echo, speak])

