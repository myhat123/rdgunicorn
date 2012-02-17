import gevent
import random

def task(pid):
    """
    Some non-deterministic task
    """
    gevent.sleep(random.randint(0,2))
    print 'Task', pid, 'done'

def synchronous():
    for i in range(1,10):
        task(i)

def asynchronous():
    threads = []
    for i in range(1,10):
        threads.append(gevent.spawn(task, i))
    gevent.joinall(threads)

print 'Synchronous:'
synchronous()

print 'Asynchronous:'
asynchronous()
