# -*- coding: utf8 -*-

import gevent

#from gevent import joinall,Timeout
#from gevent import monkey;monkey.patch_all()
#from gevent.pool import Pool

import urllib2
import socket

CONNECT_TIMEOUT,DATA_TIMEOUT = 10, 10
IP_COUNT,POOL_SIZE = 1000, 100

def curl(ip):
    '''
使用urllib2探测IP是否可以访问，并抽取应答码
和错误原因
'''
    url = 'http://' + ip
    request = urllib2.Request(url=url)
    reason, other = None, 0

    try:
        rsp = urllib2.urlopen(request, timeout=10)
        reason, other = rsp.getcode(), rsp.msg
    except urllib2.HTTPError, ex:
        reason, other = ex.code, ex.msg
    except urllib2.URLError, ex:
        reason = ex.reason
        if isinstance(reason, socket.timeout):
            reason = reason.message
        elif isinstance(reason, socket.error):
            reason = reason.strerror
    finally:
        print reason, ip, other
        return reason, ip, other

def process_results(results):
    '''
处理扫描结果，对结果进行排序并打印，
及统计各种结果的数量
'''
    results = sorted(results)
    stats = {}
    for result in results:
        error = result[0]
        stats.setdefault(error, 0)
        stats[error] = stats[error] + 1
        print result
    
    keys = sorted(stats.keys())
    for key in keys:
        print key, stats[key]

if __name__ == '__main__':
    iplist = (ip.strip()
        for i, ip
        in enumerate(open('iplist.txt', 'r'))
        if i < IP_COUNT)

    #pool = Pool(POOL_SIZE)
    #jobs = [pool.spawn(curl, ip) for ip in iplist]
    jobs = [gevent.spawn(curl, ip) for ip in iplist]
    gevent.joinall(jobs)
    results = [job.value for job in jobs]
    process_results(results)
