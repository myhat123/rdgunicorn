***************
深入Application
***************

回想一下上节关注的WSGIApplication和DjangoApplication，都有一个共同的父类Application，并且都调用了run()方法。

关注内部
========

Application的代码不长，下面来看看整个情况:

.. code-block:: python
  :linenos:

  import errno
  import os
  import sys
  import traceback


  from gunicorn.glogging import Logger
  from gunicorn import util
  from gunicorn.arbiter import Arbiter
  from gunicorn.config import Config
  from gunicorn import debug

  class Application(object):
      """\
      An application interface for configuring and loading
      the various necessities for any given web framework.
      """
      
      def __init__(self, usage=None):
          self.usage = usage
          self.cfg = None
          self.callable = None
          self.logger = None
          self.do_load_config()

      def do_load_config(self):
          try:
              self.load_config()
          except Exception, e:
              sys.stderr.write("\nError: %s\n" % str(e))
              sys.stderr.flush()
              sys.exit(1)
    
      def load_config(self):
          # init configuration
          self.cfg = Config(self.usage)
          
          # parse console args
          parser = self.cfg.parser()
          opts, args = parser.parse_args()
          
          # optional settings from apps
          cfg = self.init(parser, opts, args)
          
          # Load up the any app specific configuration
          if cfg and cfg is not None:
              for k, v in cfg.items():
                  self.cfg.set(k.lower(), v)
                  
          # Load up the config file if its found.
          if opts.config and os.path.exists(opts.config):
              cfg = {
                  "__builtins__": __builtins__,
                  "__name__": "__config__",
                  "__file__": opts.config,
                  "__doc__": None,
                  "__package__": None
              }
              try:
                  execfile(opts.config, cfg, cfg)
              except Exception:
                  print "Failed to read config file: %s" % opts.config
                  traceback.print_exc()
                  sys.exit(1)
          
              for k, v in cfg.items():
                  # Ignore unknown names
                  if k not in self.cfg.settings:
                      continue
                  try:
                      self.cfg.set(k.lower(), v)
                  except:
                      sys.stderr.write("Invalid value for %s: %s\n\n" % (k, v))
                      raise
              
          # Lastly, update the configuration with any command line
          # settings.
          for k, v in opts.__dict__.items():
              if v is None:
                  continue
              self.cfg.set(k.lower(), v)
                 
      def init(self, parser, opts, args):
          raise NotImplementedError
      
      def load(self):
          raise NotImplementedError

      def reload(self):
          self.do_load_config()
          if self.cfg.spew:
              debug.spew()
          
      def wsgi(self):
          if self.callable is None:
              self.callable = self.load()
          return self.callable
      
      def run(self):
          if self.cfg.spew:
              debug.spew()
          if self.cfg.daemon:
              util.daemonize()
          else:
              try:
                  os.setpgrp()
              except OSError, e:
                  if e[0] != errno.EPERM:
                      raise 
          try:
              Arbiter(self).run()
          except RuntimeError, e:
              sys.stderr.write("\nError: %s\n\n" % e)
              sys.stderr.flush()
              sys.exit(1)

注意其中几个地方:

1. init()和load()的定义方式
2. run()的核心内容

从WSGIApplication与DjangoApplication继承自Application，并且从init()和load()的定义看，这里采用了一个最常见的设计模式: Template Method::

  在父类一级定义好一系列的方法，作为算法的骨架结构，由不同的子类来实现不同的具体功能。

落实在Application中，我们可以看到算法的骨架结构就在__init__()和run()中，由它们来调用init()和load()两个空的方法，一旦有具体实例WSGIApplication和DjangoApplication中有实现，就调用具体实例的init()和load()。

代码流程
========

1. 初始化流程

  .. py:function:: __init__()
  .. py:function:: do_load_config()
  .. py:function:: load_config()
  .. py:function:: init(parser, opts, args)
  
2. run运行流程

  .. py:function:: run()
  .. py:function:: Arbiter(self).run()
  .. py:function:: wsgi()
  .. py:function:: load()
