import sys
import gevent
from gevent import Timeout

def wait():
    gevent.sleep(2)

try:
    timer = Timeout(1).start()

    thread1 = gevent.spawn(wait)
    thread1.join(timeout=timer)
except:
    print '1)...'
    print sys.exc_info()

# --
    try:
        timer = Timeout.start_new(1)

        thread2 = gevent.spawn(wait)
        thread2.get(timeout=timer)
    except:
        print '2)...'
        print sys.exc_info()

# --
        try:
            gevent.with_timeout(1, wait)
        except:
            print '3)...'
            print sys.exc_info()
