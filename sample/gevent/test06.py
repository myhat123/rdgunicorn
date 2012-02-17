import gevent

def run_forever():
    gevent.sleep(1000)

def main():
    thread = gevent.spawn(run_forever)
    thread.join()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'halt...'
        gevent.shutdown()
