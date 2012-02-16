**********
worker积木
**********

之所以称之为*积木*，意思就是它可以随时进行替换，也是gunicorn让人称道的地方。

同步worker
==========

默认的worker class，是同步的方式，也就是一次只能处理一个请求，且必须等待它完成后返回。对应的class SyncWorker(base.Worker)，还是进入到源代码看看吧

.. code-block:: python
  :linenos:

  import gunicorn.http as http
  import gunicorn.http.wsgi as wsgi
  import gunicorn.util as util
  import gunicorn.workers.base as base

  class SyncWorker(base.Worker):
      
      def run(self):
          # self.socket appears to lose its blocking status after
          # we fork in the arbiter. Reset it here.
          self.socket.setblocking(0)

          while self.alive:
              self.notify()
              
              # Accept a connection. If we get an error telling us
              # that no connection is waiting we fall down to the
              # select which is where we'll wait for a bit for new
              # workers to come give us some love.
              try:
                  client, addr = self.socket.accept()
                  client.setblocking(1)
                  util.close_on_exec(client)
                  self.handle(client, addr)

                  # Keep processing clients until no one is waiting. This
                  # prevents the need to select() for every client that we
                  # process.
                  continue

              except socket.error, e:
                  if e[0] not in (errno.EAGAIN, errno.ECONNABORTED):
                      raise

              # If our parent changed then we shut down.
              if self.ppid != os.getppid():
                  self.log.info("Parent changed, shutting down: %s", self)
                  return
              
              try:
                  self.notify()
                  ret = select.select([self.socket], [], self.PIPE, self.timeout)
                  if ret[0]:
                      continue
              except select.error, e:
                  if e[0] == errno.EINTR:
                      continue
                  if e[0] == errno.EBADF:
                      if self.nr < 0:
                          continue
                      else:
                          return
                  raise
      
      def handle(self, client, addr):
          try:
              parser = http.RequestParser(client)
              req = parser.next()
              self.handle_request(req, client, addr)
          except StopIteration, e:
              self.log.debug("Closing connection. %s", e)
          except socket.error, e:
              if e[0] != errno.EPIPE:
                  self.log.exception("Error processing request.")
              else:
                  self.log.debug("Ignoring EPIPE")
          except Exception, e:
              self.handle_error(client, e)
          finally:    
              util.close(client)

      def handle_request(self, req, client, addr):
          environ = {}
          try:
              self.cfg.pre_request(self, req)
              request_start = datetime.now()
              resp, environ = wsgi.create(req, client, addr,
                      self.address, self.cfg)
              # Force the connection closed until someone shows
              # a buffering proxy that supports Keep-Alive to
              # the backend.
              resp.force_close()
              self.nr += 1
              if self.nr >= self.max_requests:
                  self.log.info("Autorestarting worker after current request.")
                  self.alive = False
              respiter = self.wsgi(environ, resp.start_response)
              try:
                  if isinstance(respiter, environ['wsgi.file_wrapper']):
                      resp.write_file(respiter)
                  else:
                      for item in respiter:
                          resp.write(item)
                  resp.close()
                  request_time = datetime.now() - request_start
                  self.log.access(resp, environ, request_time)
              finally:
                  if hasattr(respiter, "close"):
                      respiter.close()
          except socket.error:
              raise
          except Exception, e:
              # Only send back traceback in HTTP in debug mode.
              self.handle_error(client, e) 
              return
          finally:
              try:
                  self.cfg.post_request(self, req, environ)
              except:
                  pass

SyncWorker总共才定义了三个方法，run()，handle()，handle_request()，真正的处理就在run()内，它是从父类base.Worker继承而来。很自然，我们就会回想起app的处理，wsgiapp/djangoapp的设计模式，从WSGIApplication与DjangoApplication继承自Application。                

观察了源代码的结构后，发现的确这种设计模式是一脉相承的。在base.Worker中，run()方法是作为一个空架子放在那里。

.. code-block:: python
  :linenos:

  class Worker(object):

      SIGNALS = map(
          lambda x: getattr(signal, "SIG%s" % x),
          "HUP QUIT INT TERM USR1 USR2 WINCH CHLD".split()
      )
      
      PIPE = []

      def __init__(self, age, ppid, socket, app, timeout, cfg, log):
          """\
          This is called pre-fork so it shouldn't do anything to the
          current process. If there's a need to make process wide
          changes you'll want to do that in ``self.init_process()``.
          """
          self.age = age
          self.ppid = ppid
          self.socket = socket
          self.app = app
          self.timeout = timeout
          self.cfg = cfg
          self.booted = False

          self.nr = 0
          self.max_requests = cfg.max_requests or sys.maxint
          self.alive = True
          self.log = log
          self.debug = cfg.debug
          self.address = self.socket.getsockname()
          self.tmp = WorkerTmp(cfg) 
          
      def __str__(self):
          return "<Worker %s>" % self.pid
          
      @property
      def pid(self):
          return os.getpid()

      def notify(self):
          """\
          Your worker subclass must arrange to have this method called
          once every ``self.timeout`` seconds. If you fail in accomplishing
          this task, the master process will murder your workers.
          """
          self.tmp.notify()

      def run(self):
          """\
          This is the mainloop of a worker process. You should override
          this method in a subclass to provide the intended behaviour
          for your particular evil schemes.
          """
          raise NotImplementedError()


在主控master那里启动worker.init_process()，恰恰就是定义在base.Worker中.

.. code-block:: python
  :linenos:

  class Worker(object):

      # ......

      def init_process(self):
          """\
          If you override this method in a subclass, the last statement
          in the function should be to call this method with
          super(MyWorkerClass, self).init_process() so that the ``run()``
          loop is initiated.
          """
          util.set_owner_process(self.cfg.uid, self.cfg.gid)

          # Reseed the random number generator
          util.seed()

          # For waking ourselves up
          self.PIPE = os.pipe()
          map(util.set_non_blocking, self.PIPE)
          map(util.close_on_exec, self.PIPE)
          
          # Prevent fd inherientence
          util.close_on_exec(self.socket)
          util.close_on_exec(self.tmp.fileno())

          self.log.close_on_exec()

          self.init_signals()
          
          self.wsgi = self.app.wsgi()
          
          # Enter main run loop
          self.booted = True
          self.run()

      def init_signals(self):
          map(lambda s: signal.signal(s, signal.SIG_DFL), self.SIGNALS)
          signal.signal(signal.SIGQUIT, self.handle_quit)
          signal.signal(signal.SIGTERM, self.handle_exit)
          signal.signal(signal.SIGINT, self.handle_exit)
          signal.signal(signal.SIGWINCH, self.handle_winch)
          signal.signal(signal.SIGUSR1, self.handle_usr1)
          # Don't let SIGQUIT and SIGUSR1 disturb active requests
          # by interrupting system calls
          if hasattr(signal, 'siginterrupt'):  # python >= 2.6
              signal.siginterrupt(signal.SIGQUIT, False)
              signal.siginterrupt(signal.SIGUSR1, False)

在init_process()执行了子类包括SyncWorker的run()方法。              

异步worker
==========

异步worker分两种，一个是Eventlet，另一个就是大名鼎鼎的gevent。整体的设计模式，与同步worker类似，都是采用的template pattern。

EventletWorker
--------------

EventletWorker继承路线上是分成了三级:

.. py:class:: class EventletWorker(AsyncWorker)
.. py:class:: class AsyncWorker(base.Worker)

先看EventletWorker

.. code-block:: python
  :linenos:

  from __future__ import with_statement


  import os
  try:
      import eventlet
  except ImportError:
      raise RuntimeError("You need eventlet installed to use this worker.")
  from eventlet import hubs
  from eventlet.greenio import GreenSocket

  from gunicorn.workers.async import AsyncWorker

  class EventletWorker(AsyncWorker):

      @classmethod
      def setup(cls):
          import eventlet
          if eventlet.version_info < (0,9,7):
              raise RuntimeError("You need eventlet >= 0.9.7")
          eventlet.monkey_patch(os=False)

      def init_process(self):
          hubs.use_hub()
          super(EventletWorker, self).init_process()
          
      def timeout_ctx(self):
          return eventlet.Timeout(self.cfg.keepalive, False) 

      def run(self):
          self.socket = GreenSocket(family_or_realsock=self.socket.sock)
          self.socket.setblocking(1)
          self.acceptor = eventlet.spawn(eventlet.serve, self.socket,
                  self.handle, self.worker_connections)

          while self.alive:
              self.notify()
              if self.ppid != os.getppid():
                  self.log.info("Parent changed, shutting down: %s", self)
                  break

              eventlet.sleep(1.0)

          self.notify()
          with eventlet.Timeout(self.timeout, False):
              eventlet.kill(self.acceptor, eventlet.StopServe)

run()方法中的语句::

  self.acceptor = eventlet.spawn(eventlet.serve, self.socket,
                  self.handle, self.worker_connections)

调用的是:
  
.. py:function:: eventlet.serve(sock, handle, concurrency=1000)
  
这里包含了self.handle，这个方法在AsyncWorker中声明定义

.. code-block:: python
  :linenos:

  class AsyncWorker(base.Worker):

      def __init__(self, *args, **kwargs):
          super(AsyncWorker, self).__init__(*args, **kwargs)
          self.worker_connections = self.cfg.worker_connections
      
      def timeout_ctx(self):
          raise NotImplementedError()

      def handle(self, client, addr):
          try:
              parser = http.RequestParser(client)
              try:
                  while True:
                      req = None
                      with self.timeout_ctx():
                          req = parser.next()
                      if not req:
                          break
                      self.handle_request(req, client, addr)
              except StopIteration, e:
                  self.log.debug("Closing connection. %s", e)
          except socket.error, e:
              if e[0] not in (errno.EPIPE, errno.ECONNRESET):
                  self.log.exception("Socket error processing request.")
              else:
                  if e[0] == errno.ECONNRESET:
                      self.log.debug("Ignoring connection reset")
                  else:
                      self.log.debug("Ignoring EPIPE")
          except Exception, e:
              self.handle_error(client, e)
          finally:
              util.close(client)

      def handle_request(self, req, sock, addr):
          try:
              self.cfg.pre_request(self, req)
              request_start = datetime.now()
              resp, environ = wsgi.create(req, sock, addr, self.address, self.cfg)
              self.nr += 1
              if self.alive and self.nr >= self.max_requests:
                  self.log.info("Autorestarting worker after current request.")
                  resp.force_close()
                  self.alive = False
              respiter = self.wsgi(environ, resp.start_response)
              if respiter == ALREADY_HANDLED:
                  return False
              try:
                  for item in respiter:
                      resp.write(item)
                  resp.close()
                  request_time = datetime.now() - request_start
                  self.log.access(resp, environ, request_time)
              finally:
                  if hasattr(respiter, "close"):
                    respiter.close()
              if resp.should_close():
                  raise StopIteration()
          finally:
              try:
                  self.cfg.post_request(self, req, environ)
              except:
                  pass
          return True

GeventWorker
------------

这里的代码关系要复杂一些

.. code-block:: python
  :linenos:
 
  class GeventWorker(AsyncWorker):

      server_class = None
      wsgi_handler = None

      @classmethod  
      def setup(cls):
          from gevent import monkey
          monkey.noisy = False
          monkey.patch_all()
          
          
      def timeout_ctx(self):
          return gevent.Timeout(self.cfg.keepalive, False)

      def run(self):
          self.socket.setblocking(1)

          pool = Pool(self.worker_connections)
          if self.server_class is not None:
              server = self.server_class(
                  self.socket, application=self.wsgi, spawn=pool, log=self.log,
                  handler_class=self.wsgi_handler)
          else:
              server = StreamServer(self.socket, handle=self.handle, spawn=pool)

          server.start()
          try:
              while self.alive:
                  self.notify()
                  if self.ppid != os.getppid():
                      self.log.info("Parent changed, shutting down: %s", self)
                      break
          
                  gevent.sleep(1.0)
                  
          except KeyboardInterrupt:
              pass

          try:
              # Try to stop connections until timeout
              self.notify()
              server.stop(timeout=self.timeout)
          except:
              pass

      def handle_request(self, *args):
          try:
              super(GeventWorker, self).handle_request(*args)
          except gevent.GreenletExit:
              pass

      if hasattr(gevent.core, 'dns_shutdown'):

          def init_process(self):
              #gevent 0.13 and older doesn't reinitialize dns for us after forking
              #here's the workaround
              gevent.core.dns_shutdown(fail_requests=1)
              gevent.core.dns_init()
              super(GeventWorker, self).init_process()

主要的焦点在::

  server = self.server_class(
                  self.socket, application=self.wsgi, spawn=pool, log=self.log,
                  handler_class=self.wsgi_handler)

而self.server_class和self.wsgi_handler都是空值，怎么能使用呢？

再继续往下看，原来它派生出了一个子类

.. code-block:: python

  class GeventPyWSGIWorker(GeventWorker):
      "The Gevent StreamServer based workers."
      server_class = PyWSGIServer
      wsgi_handler = PyWSGIHandler

在gunicorn的代码树中，唯一没有介绍到的只有http目录了，下一步进入http      
