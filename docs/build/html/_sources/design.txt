****
设计
****

这部分是采用gunicorn的英文文档，同时加入自己的理解，源代码，以及参考资料等等

服务器模型
==========

gunicorn是基于"pre-fork worker"模型，这就意味着有一个中心主控master进程，由它来管理一组worker进程。这个主控进程并不知晓任何客户端，所有的请求和响应都完全是由多个worker进程来处理

解释pre-fork
------------

pre-fork服务器和fork服务器相似，通过一个单独的进程来处理每条请求。

不同的是，pre-fork服务器会通过预先开启大量的进程，等待并处理接到的请求。

由于采用了这种方式来开启进程，服务器并不需要等待新的进程启动而消耗时间，因而能够以更快的速度应付多用户请求。

另外，pre-fork服务器在遇到极大的高峰负载时仍能保持良好的性能状态。这是因为不管什么时候，只要预先设定的所有进程都已被用来处理请求时，服务器仍可追加额外的进程。

缺点是，当遇到高峰负载时，由于要启动新的服务器进程，不可避免地会带来响应的延迟。

主控master进程
==============

主控master进程，就是一个简单的循环，用来不断侦听不同进程信号并作出不同的动作，仅此而已。它通过一些信号，诸如TTIN, TTOU, 和CHLD等等， 管理着那些正在运行的worker进程。

TTIN 和 TTOU信号是告诉主控master进程增加或减少正在运行的worker数量。

CHLD信号是在一个子进程已经中止之后，由主控master进程重启这个失效的worker进程。

我们看几段代码，在gunicorn/arbiter.py中

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

在上面代码中的第23行中，列举了相应的多个信号：

* HUP，重启所有的配置和所有的worker进程
* QUIT，正常关闭，它会等待所有worker进程处理完各自的东西后关闭
* INT/TERM，立即关闭，强行中止所有的处理
* TTIN，增加一个worker进程
* TTOU，减少一个worker进程
* USR1，重新打开由master和worker所有的日志处理
* USR2，重新运行master和worker
* WINCH，正常关闭所有worker进程，保持主控master进程的运行

下面是针对不同信号的代码:

.. code-block:: python
  :linenos:

  def handle_chld(self, sig, frame):
      "SIGCHLD handling"
      self.wakeup()
      
  def handle_hup(self):
      """\
      HUP handling.
      - Reload configuration
      - Start the new worker processes with a new configuration
      - Gracefully shutdown the old worker processes
      """
      self.log.info("Hang up: %s", self.master_name)
      self.reload()
      
  def handle_quit(self):
      "SIGQUIT handling"
      raise StopIteration
  
  def handle_int(self):
      "SIGINT handling"
      self.stop(False)
      raise StopIteration
  
  def handle_term(self):
      "SIGTERM handling"
      self.stop(False)
      raise StopIteration

  def handle_ttin(self):
      """\
      SIGTTIN handling.
      Increases the number of workers by one.
      """
      self.num_workers += 1
      self.manage_workers()
  
  def handle_ttou(self):
      """\
      SIGTTOU handling.
      Decreases the number of workers by one.
      """
      if self.num_workers <= 1:
          return
      self.num_workers -= 1
      self.manage_workers()

  def handle_usr1(self):
      """\
      SIGUSR1 handling.
      Kill all workers by sending them a SIGUSR1
      """
      self.kill_workers(signal.SIGUSR1)
      self.log.reopen_files()
  
  def handle_usr2(self):
      """\
      SIGUSR2 handling.
      Creates a new master/worker set as a slave of the current
      master without affecting old workers. Use this to do live
      deployment with the ability to backout a change.
      """
      self.reexec()
      
  def handle_winch(self):
      "SIGWINCH handling"
      if os.getppid() == 1 or os.getpgrp() != os.getpid():
          self.log.info("graceful stop of workers")
          self.num_workers = 0
          self.kill_workers(signal.SIGQUIT)
      else:
          self.log.info("SIGWINCH ignored. Not daemonized")

同步workers
===========

大多数情况下，采用的worker类型是同步方式，也就是说一次仅处理一个请求。这种模型方式是最简单的，因为期间发生的任何错误最多只影响到一个请求。

尽管下面我们描述的内容，也是一次处理一个请求，但实际上在编写应用的时候，是加一些条件的。（？？）

异步workers
===========

可用的异步workers，主要是基于greenlets软件包（通过eventlet和gevent）。greenlet是用python来实现的协程方式（cooperative multi-threading）。通常情况下，我们编写的应用代码不需要作出什么改变，就能使用上这些异步workers的特性的。

tornado workers
===============

还有一个可以用上的worker，是tornado worker，它是用在那些采用tornado框架的程序上。尽管tornado worker也可以用于wsgi程序上，但是这不是一个推荐的做法。

选择worker进程类型
==================

默认的同步worker在cpu和带宽方面会消耗资源的。这就意味着你的应用不可能无节制地做任何事。例如，互联网上的一个请求，必须要遵守这个准则。

这个资源绑定的条件，也就是为什么我们会在gunicorn默认配置前做一个缓冲的代理。如果你把同步worker，直接暴露在internet上，一个dos(Denial of Service)攻击就会给服务器不停地制造大流量无用数据，而是服务器无法正常提供服务。Slowloris，就是这样一个有趣的例子，专门用来做这事的。

有些情况可以考虑采用异步worker：

* 需要长时间阻塞调用的应用，比如外部的web service
* 直接给internet提供服务
* 流请求和响应（是类似flv流么？）
* 长轮询
* Web sockets（WebSocket是HTML5规格中的一个非常重要的新特性，它的存在可以允许用户在浏览器中实现双向通信，实现数据的及时推送）
* Comet（基于 HTTP 长连接的“服务器推”技术，是一种新的 Web 应用架构。基于这种架构开发的应用中，服务器端会主动以异步的方式向客户端程序推送数据，而不需要客户端显式的发出请求。Comet 架构非常适合事件驱动的 Web 应用，以及对交互性和实时性要求很强的应用）

启动多少个workers?
==================

不要试图做这样的事，你预期多少个客户端就启用多少个worker。gunicorn只需要启用4--12个workers，就足以每秒钟处理几百甚至上千个请求了。

在处理请求时，gunicorn依靠操作系统来提供负载均衡。通常我们推荐的worker数量是：(2 x $num_cores) + 1，这个公式很简单，它是基于给定的核心处理器数量，在其他worker处理请求时，每个worker将从socket那进行读写操作。

很显然，你的硬件环境和应用将影响到worker数量。我们推荐先采用上述公式来安排，在应用启动之后，然后再通过TTIN和TTOU这两个信号来调整worker数量。

记住：太多的worker，肯定会在某一个时刻，让你的整个系统急剧降低性能。（只能意译了）
