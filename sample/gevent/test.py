from gevent import monkey; monkey.patch_all()
import gevent
import urllib2 

def read_url(url):
    print url
    response = urllib2.urlopen(url)
    print response.getcode(), response.msg

def gethostlist():
    fp = open('iplist.txt', 'r')

    hostlist = []

    for line in fp.readlines():
        hostlist.append(r'http://' + line[:-1])

    return hostlist

def main():
    hosts = gethostlist()
    threads = []
    for x in hosts:
        a = gevent.spawn(read_url, x)
        threads.append(a)

    gevent.joinall(threads)

if __name__ == '__main__':
    main()

