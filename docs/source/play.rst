********
自己动手
********

我们再来看看用自定义配置文件

.. code-block:: python

  #import multiprocessing

  bind = "127.0.0.1:8000"
  #workers = multiprocessing.cpu_count() * 2 + 1

  worker_class = "sync"
  #worker_class = "gevent_pywsgi"
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

执行很简单::
 
  gunicorn -c myconf.py myapp:app

输出结果::

  (mypy)hzg@gofast:~/work/rdgunicorn/sample$ gunicorn -c myconf.py myapp:app
  2012-02-19 20:05:43 [2139] [INFO] Starting gunicorn 0.13.4
  2012-02-19 20:05:43 [2139] [DEBUG] Arbiter booted
  2012-02-19 20:05:43 [2139] [INFO] Listening at: http://127.0.0.1:8000 (2139)
  2012-02-19 20:05:43 [2139] [INFO] Using worker: sync
  2012-02-19 20:05:43 [2142] [INFO] Booting worker with pid: 2142
  2012-02-19 20:05:50 [2142] [DEBUG] GET /
  2012-02-19 20:06:16 [2139] [INFO] Handling signal: winch
  2012-02-19 20:06:16 [2139] [INFO] SIGWINCH ignored. Not daemonized
  2012-02-19 20:07:37 [2139] [INFO] Handling signal: ttin
  2012-02-19 20:07:37 [2207] [INFO] Booting worker with pid: 2207
  2012-02-19 20:07:55 [2139] [INFO] Handling signal: ttou
  2012-02-19 20:07:55 [2142] [INFO] Worker exiting (pid: 2142)

看到其中的ttin, ttou，就是用来增加和中止worker进程，怎么做呢？::

  $ kill -TTIN 2139
  $ kill -TTOU 2139
