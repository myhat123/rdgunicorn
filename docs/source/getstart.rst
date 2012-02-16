********
快速入门
********

安装gunicorn
============

下载源代码::
  
  git clone https://github.com/benoitc/gunicorn.git

使用开发模式来安装，便于今后调试::
  
  python setup.py develop

这样安装后，会在pythone的site-packages中仅仅增加一个链接，在自己目录下的源代码可以随时进行调整测试

简单的wsgi应用
==============

随便编写一个myapp.py

.. code-block:: python
  :linenos:

  # -*- coding: utf8 -*-

  def app(environ, start_response):
      data = "Hello, World!\n"
      start_response("200 OK", [
          ("Content-Type", "text/plain"),
          ("Content-Length", str(len(data)))
      ])
      return iter([data])

运行之::

  $ gunicorn --workers=2 myapp:app

运行的结果::

  2012-02-13 10:48:02 [2481] [INFO] Starting gunicorn 0.13.4
  2012-02-13 10:48:02 [2481] [INFO] Listening at: http://127.0.0.1:8000 (2481)
  2012-02-13 10:48:02 [2481] [INFO] Using worker: sync
  2012-02-13 10:48:02 [2484] [INFO] Booting worker with pid: 2484
  2012-02-13 10:48:02 [2485] [INFO] Booting worker with pid: 2485

简单的django应用
================

快速体验::

  $ django-admin.py startproject hello
  $ cd hello
  $ gunicorn_django --workers=2

运行结果::

  2012-02-13 11:11:15 [2565] [INFO] Starting gunicorn 0.13.4
  2012-02-13 11:11:15 [2565] [INFO] Listening at: http://127.0.0.1:8000 (2565)
  2012-02-13 11:11:15 [2565] [INFO] Using worker: sync
  2012-02-13 11:11:15 [2568] [INFO] Booting worker with pid: 2568
  2012-02-13 11:11:15 [2569] [INFO] Booting worker with pid: 2569

命令行参数
==========

执行gunicorn::

  (mypy)hzg@gofast:~/gunicorn$ gunicorn -h
  Usage: gunicorn [OPTIONS] APP_MODULE

  Options:
    --version             show program's version number and exit
    -h, --help            show this help message and exit
    -c FILE, --config=FILE
                          The path to a Gunicorn config file. [None]
    --debug               Turn on debugging in the server. [False]
    --spew                Install a trace function that spews every line
                          executed by the server. [False]
    --access-logfile=FILE
                          The Access log file to write to. [None]
    --access-logformat=STRING
                          The Access log format . [%(h)s %(l)s %(u)s %(t)s
                          "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"]
    --error-logfile=FILE, --log-file=FILE
                          The Error log file to write to. [-]
    --log-level=LEVEL     The granularity of Error log outputs. [info]
    --logger-class=STRING
                          The logger you want to use to log events in gunicorn.
                          [simple]
    -n STRING, --name=STRING
                          A base to use with setproctitle for process naming.
                          [None]
    --preload             Load application code before the worker processes are
                          forked. [False]
    -D, --daemon          Daemonize the Gunicorn process. [False]
    -p FILE, --pid=FILE   A filename to use for the PID file. [None]
    -u USER, --user=USER  Switch worker processes to run as this user. [1000]
    -g GROUP, --group=GROUP
                          Switch worker process to run as this group. [1000]
    -m INT, --umask=INT   A bit mask for the file mode on files written by
                          Gunicorn. [0]
    -b ADDRESS, --bind=ADDRESS
                          The socket to bind. [127.0.0.1:8000]
    --backlog=INT         The maximum number of pending connections.     [2048]
    -w INT, --workers=INT
                          The number of worker process for handling requests.
                          [1]
    -k STRING, --worker-class=STRING
                          The type of workers to use. [sync]
    --worker-connections=INT
                          The maximum number of simultaneous clients. [1000]
    --max-requests=INT    The maximum number of requests a worker will process
                          before restarting. [0]
    -t INT, --timeout=INT
                          Workers silent for more than this many seconds are
                          killed and restarted. [30]
    --keep-alive=INT      The number of seconds to wait for requests on a Keep-
                          Alive connection. [2]
