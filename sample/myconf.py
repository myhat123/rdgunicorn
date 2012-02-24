import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1

#worker_class = "sync"
#worker_class = "gevent"
worker_class = "gevent_pywsgi"
#worker_class = "gevent_wsgi"
#worker_class = "egg:gunicorn#tornado"
#worker_class = "gunicorn.workers.ggevent.GeventWorker"

worker_connections = 100

timeout = 50

loglevel = 'debug'

proc_name = 'justforfun'

def post_fork(server, worker):
    #server.log.info("Worker spawned (pid: %s)", worker.pid)
    pass

def pre_fork(server, worker):
    #server.log.info("Pre fork ...")
    pass
