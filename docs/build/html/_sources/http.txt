****************
自带的httpserver
****************

gunicorn自带了一个python wsgi http server，是为了默认的syncworker而设计的。

.. code-block:: python

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

终于在这里看到了久违的self.socket.accept()，接收一个访问连接，由self.handle(client, addr)来处理客户端来的请求命令。

.. code-block:: python

  class SyncWorker(base.Worker):

      #......

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

从http.RequestParser(client)进入http模块中，在self.handle_request(req, client, addr)中调用wsgi模块

.. code-block:: python

  class SyncWorker(base.Worker):

      #......

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

其中涉及到wsgi模块的有::

  resp, environ = wsgi.create(req, client, addr,
                      self.address, self.cfg)

获得最终的响应结果::                      

  respiter = self.wsgi(environ, resp.start_response)

这里的self.wsgi的踪迹在哪里呢？

1. 由base.Worker中的方法init_process()中调用

.. code-block:: python

  self.init_signals()
      
  self.wsgi = self.app.wsgi()
  
  # Enter main run loop
  self.booted = True
  self.run()

2. 在app，也就是wsgiapp或djangoapp中WSGIApplication -> Application中，有

.. code-block:: python

  def wsgi(self):
      if self.callable is None:
          self.callable = self.load()
      return self.callable

3. 直接由self.load()执行，回转到WSGIApplication中的load()

.. code-block:: python

  def load(self):
      return util.import_app(self.app_uri)

4. 调用util模块中的import_app(self.app_uri)

.. code-block:: python

  def import_app(module):
      parts = module.split(":", 1)
      if len(parts) == 1:
          module, obj = module, "application"
      else:
          module, obj = parts[0], parts[1]

      try:
          __import__(module)
      except ImportError:
          if module.endswith(".py") and os.path.exists(module):
              raise ImportError("Failed to find application, did "
                  "you mean '%s:%s'?" % (module.rsplit(".",1)[0], obj))
          else:
              raise

      mod = sys.modules[module]
      app = eval(obj, mod.__dict__)
      if app is None:
          raise ImportError("Failed to find application object: %r" % obj)
      if not callable(app):
          raise TypeError("Application object must be callable.")
      return app

这才是最终wsgi应用程序的发起。还记得我们在快速入门中编写的简单wsgi程序么?

那么我们就在这里加上一句print，看看是不是:

.. code-block:: python

  print u'waiting for you ...(%s, %s)' % (module, obj)

再执行命令::

  $ gunicorn --workers=2 myapp:app

结果如下::

  (mypy)hzg@xubuntu:~/sample$ gunicorn --workers=2 myapp:app
  2012-02-16 08:45:09 [2007] [INFO] Starting gunicorn 0.13.4
  2012-02-16 08:45:09 [2007] [INFO] Listening at: http://127.0.0.1:8000 (2007)
  2012-02-16 08:45:09 [2007] [INFO] Using worker: sync
  2012-02-16 08:45:09 [2010] [INFO] Booting worker with pid: 2010
  waiting for you ...(myapp, app)
  2012-02-16 08:45:09 [2011] [INFO] Booting worker with pid: 2011
  waiting for you ...(myapp, app)

