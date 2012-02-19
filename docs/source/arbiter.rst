************
真正的主宰者
************

循环主体
========

通过上面的抽丝拨茧，进入到Arbiter类，这个才是真正的主宰者。在前面涉及gunicorn设计一节中，已经讲到了部分Arbiter的信号处理，这里将详细介绍run()方法。

.. code-block:: python
  :linenos:

  class Arbiter(object):
      """
      Arbiter maintain the workers processes alive. It launches or
      kills them if needed. It also manages application reloading
      via SIGHUP/USR2.
      """

      # A flag indicating if a worker failed to
      # to boot. If a worker process exist with
      # this error code, the arbiter will terminate.
      WORKER_BOOT_ERROR = 3

      START_CTX = {}
      
      LISTENER = None
      WORKERS = {}    
      PIPE = []

      # I love dynamic languages
      SIG_QUEUE = []
      SIGNALS = map(
          lambda x: getattr(signal, "SIG%s" % x),
          "HUP QUIT INT TERM TTIN TTOU USR1 USR2 WINCH".split()
      )
      SIG_NAMES = dict(
          (getattr(signal, name), name[3:].lower()) for name in dir(signal)
          if name[:3] == "SIG" and name[3] != "_"
      )
      
      def __init__(self, app):
          os.environ["SERVER_SOFTWARE"] = SERVER_SOFTWARE

          self.setup(app)
          
          self.pidfile = None
          self.worker_age = 0
          self.reexec_pid = 0
          self.master_name = "Master"
          
          # get current path, try to use PWD env first
          try:
              a = os.stat(os.environ['PWD'])
              b = os.stat(os.getcwd())
              if a.ino == b.ino and a.dev == b.dev:
                  cwd = os.environ['PWD']
              else:
                  cwd = os.getcwd()
          except:
              cwd = os.getcwd()
              
          args = sys.argv[:]
          args.insert(0, sys.executable)

          # init start context
          self.START_CTX = {
              "args": args,
              "cwd": cwd,
              0: sys.executable
          }
          
      def setup(self, app):
          self.app = app
          self.cfg = app.cfg
          self.log = self.cfg.logger_class(app.cfg)
      
          if 'GUNICORN_FD' in os.environ:
              self.log.reopen_files()
          
          self.address = self.cfg.address
          self.num_workers = self.cfg.workers
          self.debug = self.cfg.debug
          self.timeout = self.cfg.timeout
          self.proc_name = self.cfg.proc_name
          self.worker_class = self.cfg.worker_class
          
          if self.cfg.debug:
              self.log.debug("Current configuration:")
              for config, value in sorted(self.cfg.settings.iteritems()):
                  self.log.debug("  %s: %s", config, value.value)
          
          if self.cfg.preload_app:
              if not self.cfg.debug:
                  self.app.wsgi()
              else:
                  self.log.warning("debug mode: app isn't preloaded.")

      def start(self):
          """\
          Initialize the arbiter. Start listening and set pidfile if needed.
          """
          self.log.info("Starting gunicorn %s", __version__)
          self.cfg.on_starting(self)
          self.pid = os.getpid()
          self.init_signals()
          if not self.LISTENER:
              self.LISTENER = create_socket(self.cfg, self.log)
          
          if self.cfg.pidfile is not None:
              self.pidfile = Pidfile(self.cfg.pidfile)
              self.pidfile.create(self.pid)
          self.log.debug("Arbiter booted")
          self.log.info("Listening at: %s (%s)", self.LISTENER,
              self.pid)
          self.log.info("Using worker: %s",
                  self.cfg.settings['worker_class'].get())

          self.cfg.when_ready(self)
      
      def init_signals(self):
          """\
          Initialize master signal handling. Most of the signals
          are queued. Child signals only wake up the master.
          """
          if self.PIPE:
              map(os.close, self.PIPE)
          self.PIPE = pair = os.pipe()
          map(util.set_non_blocking, pair)
          map(util.close_on_exec, pair)
          self.log.close_on_exec()
          map(lambda s: signal.signal(s, self.signal), self.SIGNALS)
          signal.signal(signal.SIGCHLD, self.handle_chld)

      def signal(self, sig, frame):
          if len(self.SIG_QUEUE) < 5:
              self.SIG_QUEUE.append(sig)
              self.wakeup()

      def run(self):
          "Main master loop."
          self.start()
          util._setproctitle("master [%s]" % self.proc_name)
          
          self.manage_workers()
          while True:
              try:
                  self.reap_workers()
                  sig = self.SIG_QUEUE.pop(0) if len(self.SIG_QUEUE) else None
                  if sig is None:
                      self.sleep()
                      self.murder_workers()
                      self.manage_workers()
                      continue
                  
                  if sig not in self.SIG_NAMES:
                      self.log.info("Ignoring unknown signal: %s", sig)
                      continue
                  
                  signame = self.SIG_NAMES.get(sig)
                  handler = getattr(self, "handle_%s" % signame, None)
                  if not handler:
                      self.log.error("Unhandled signal: %s", signame)
                      continue
                  self.log.info("Handling signal: %s", signame)
                  handler()  
                  self.wakeup()
              except StopIteration:
                  self.halt()
              except KeyboardInterrupt:
                  self.halt()
              except HaltServer, inst:
                  self.halt(reason=inst.reason, exit_status=inst.exit_status)
              except SystemExit:
                  raise
              except Exception:
                  self.log.info("Unhandled exception in main loop:\n%s",  
                              traceback.format_exc())
                  self.stop(False)
                  if self.pidfile is not None:
                      self.pidfile.unlink()
                  sys.exit(-1)

正如在设计一节中说到的，主控master进程，就是一个简单的循环，用来不断侦听各种信号，然后作出不同的动作。    

* 130行，start()，用来创建一个侦听用的socket，并创建一个pidfile（就是进程号文件），放在/tmp下
* 133行，manage_workers()
* 134行，正式进入循环体

核心语句
========

那下面我们感兴趣的地方，自然是落在那些信号的初始化上，仔细进入start()里面看看，start()中主要的语句在::

  self.pid = os.getpid()
  self.init_signals()
  if not self.LISTENER:
      self.LISTENER = create_socket(self.cfg, self.log)
  
  if self.cfg.pidfile is not None:
      self.pidfile = Pidfile(self.cfg.pidfile)
      self.pidfile.create(self.pid)

self.init_signals()::

  #对预设的各种信号进行map处理
  map(lambda s: signal.signal(s, self.signal), self.SIGNALS)
  signal.signal(signal.SIGCHLD, self.handle_chld)

各种信号就是Arbiter的类变量::
  
  SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM TTIN TTOU USR1 USR2 WINCH".split()
    )

这里运用了python有趣的动态语言特性，lambda，map，那这些信号map之后，到哪去了呢？注意看self.signal()

.. code-block:: python

  def signal(self, sig, frame):
      if len(self.SIG_QUEUE) < 5:
          self.SIG_QUEUE.append(sig)
          self.wakeup()

把所有的信号放进一个信号列表，然后执行wakeup()。

进入run()中的循环体之后，真正处理信号的就是handle()，而这个对应的是各种信号的处理handle_xxx()。真正管理用户请求和响应的，并不是在arbiter中处理，而是交给了worker。所以注意看manage_worker()和spawn_worker()

manage_worker()代码

.. code-block:: python
  :linenos:

  def manage_workers(self):
          """\
          Maintain the number of workers by spawning or killing
          as required.
          """
          if len(self.WORKERS.keys()) < self.num_workers:
              self.spawn_workers()

          workers = self.WORKERS.items()
          workers.sort(key=lambda w: w[1].age)
          while len(workers) > self.num_workers:
              (pid, _) = workers.pop(0)
              self.kill_worker(pid, signal.SIGQUIT)

根据worker数量，如果小于配置中的数量，就生成一个worker进程，否则中断worker进程              

spawn_worker()代码

.. code-block:: python
  :linenos:

  def spawn_worker(self):
      self.worker_age += 1
      worker = self.worker_class(self.worker_age, self.pid, self.LISTENER,
                                  self.app, self.timeout/2.0,
                                  self.cfg, self.log)
      self.cfg.pre_fork(self, worker)
      pid = os.fork()
      if pid != 0:
          self.WORKERS[pid] = worker
          return pid

      # Process Child
      worker_pid = os.getpid()
      try:
          util._setproctitle("worker [%s]" % self.proc_name)
          self.log.info("Booting worker with pid: %s", worker_pid)
          self.cfg.post_fork(self, worker)
          worker.init_process()
          sys.exit(0)
      except SystemExit:
          raise
      except:
          self.log.exception("Exception in worker process:")
          if not worker.booted:
              sys.exit(self.WORKER_BOOT_ERROR)
          sys.exit(-1)
      finally:
          self.log.info("Worker exiting (pid: %s)", worker_pid)
          try:
              worker.tmp.close()
              self.cfg.worker_exit(self, worker)
          except:
              pass

其中::

  worker = self.worker_class(self.worker_age, self.pid, self.LISTENER,
                                  self.app, self.timeout/2.0,
                                  self.cfg, self.log)
  ......

  worker.init_process()

由此进入worker枢纽环节，将在后续介绍之。

self.cfg.pre_fork(self, worker)是server hook之一。代码在哪呢？在config.py中

.. code-block:: python

  class Prefork(Setting):
      name = "pre_fork"
      section = "Server Hooks"
      validator = validate_callable(2)
      type = "callable"
      def pre_fork(server, worker):
          pass
      default = staticmethod(pre_fork)
      desc = """\
          Called just before a worker is forked.
          
          The callable needs to accept two instance variables for the Arbiter and
          new Worker.
          """

可以在自定义的配置文件中定义。之后的self.cfg.post_fork(self, worker)，self.cfg.worker_exit(self, worker)都是在config.py中作为server hook::

  pid = os.fork()
  worker_pid = os.getpid()

这是我们熟知的进程处理方式。  
