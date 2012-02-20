from gevent import monkey; monkey.patch_all()
from gevent import Timeout
from gevent.pool import Pool

import gevent
import urllib2 

def read_url(url):
    timeout = Timeout(10)
    timeout.start()
    try:
        response = urllib2.urlopen(url)
        reason, other = response.getcode(), response.msg
    except Timeout, t:
        reason, other = 'gevent timeout', 0
    except urllib2.HTTPeRROR, ex:
        reason, other = ex.code, ex.msg
    except urllib2.URLError, ex:
        reason = ex.reason
    finally:
        timeout.cancel()
        print url, reason, other

def gethostlist():
    fp = open('iplist.txt', 'r')

    hostlist = []

    for line in fp.readlines():
        hostlist.append(r'http://' + line[:-1])

    return hostlist

def main():
    pool = Pool(10)

    hosts = gethostlist()
    threads = []
    for x in hosts:
        #a = gevent.spawn(read_url, x)
        pool.spawn(read_url, x)
        #threads.append(a)

    #gevent.joinall(threads)
    pool.join()

if __name__ == '__main__':
    main()

