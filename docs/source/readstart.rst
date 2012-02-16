******************
从哪开始阅读源代码
******************

代码树
======

执行命令::

  tree -I '*.pyc' 

先看看gunicorn的目录树::

  gunicorn
  ├── app
  │   ├── base.py
  │   ├── djangoapp.py
  │   ├── __init__.py
  │   ├── pasterapp.py
  │   └── wsgiapp.py
  ├── arbiter.py
  ├── config.py
  ├── debug.py
  ├── errors.py
  ├── glogging.py
  ├── http
  │   ├── body.py
  │   ├── errors.py
  │   ├── __init__.py
  │   ├── message.py
  │   ├── parser.py
  │   ├── _sendfile.py
  │   ├── unreader.py
  │   └── wsgi.py
  ├── __init__.py
  ├── logging_config.py
  ├── management
  │   ├── commands
  │   │   ├── __init__.py
  │   │   └── run_gunicorn.py
  │   └── __init__.py
  ├── pidfile.py
  ├── sock.py
  ├── util.py
  └── workers
      ├── async.py
      ├── base.py
      ├── geventlet.py
      ├── ggevent.py
      ├── ggevent_wsgi.py
      ├── gtornado.py
      ├── __init__.py
      ├── sync.py
      └── workertmp.py

从脚本命令开始
==============

就从脚本命令gunicorn和gunicorn_django开始

gunicorn

.. code-block:: python

  #!/home/hzg/mypy/bin/python
  # EASY-INSTALL-ENTRY-SCRIPT: 'gunicorn==0.13.4','console_scripts','gunicorn'
  __requires__ = 'gunicorn==0.13.4'
  import sys
  from pkg_resources import load_entry_point

  sys.exit(
     load_entry_point('gunicorn==0.13.4', 'console_scripts', 'gunicorn')()
  )

gunicorn_django

.. code-block:: python

  #!/home/hzg/mypy/bin/python
  # EASY-INSTALL-ENTRY-SCRIPT: 'gunicorn==0.13.4','console_scripts','gunicorn_django'
  __requires__ = 'gunicorn==0.13.4'
  import sys
  from pkg_resources import load_entry_point

  sys.exit(
     load_entry_point('gunicorn==0.13.4', 'console_scripts', 'gunicorn_django')()
  )

这是eggs文件的规范，实际上调用入口，可以从entry_points.txt看出来：

entry_points.txt::

  [console_scripts]
  gunicorn=gunicorn.app.wsgiapp:run
  gunicorn_django=gunicorn.app.djangoapp:run
  gunicorn_paster=gunicorn.app.pasterapp:run

注意在[console_scripts]部分，有

* gunicorn <--> gunicorn.app.wsgiapp:run 
* gunicorn_django <--> gunicorn.app.djangoapp:run

那么，我们就从gunicorn/app目录下开始，从wsgiapp.py, djangoapp.py开始。

wsgiapp.py
----------

.. code-block:: python
  :linenos:

  import os
  import sys

  from gunicorn import util
  from gunicorn.app.base import Application

  class WSGIApplication(Application):
      
      def init(self, parser, opts, args):
          if len(args) != 1:
              parser.error("No application module specified.")

          self.cfg.set("default_proc_name", args[0])
          self.app_uri = args[0]

          sys.path.insert(0, os.getcwd())

      def load(self):
          return util.import_app(self.app_uri)

  def run():
      """\
      The ``gunicorn`` command line runner for launcing Gunicorn with
      generic WSGI applications.
      """
      from gunicorn.app.wsgiapp import WSGIApplication
      WSGIApplication("%prog [OPTIONS] APP_MODULE").run()

gunicorn.app.wsgiapp:run最终是调用其中的一个函数run()，焦点集中在上述代码的最后两行，创建WSGIApplication后，立刻执行run()。

djangoapp.py
------------

.. code-block:: python
  :linenos:

  ENVIRONMENT_VARIABLE = 'DJANGO_SETTINGS_MODULE'

  class DjangoApplication(Application):
      
      def init(self, parser, opts, args):
          self.global_settings_path = None
          self.project_path = None
          if args:
              self.global_settings_path = args[0]
              if not os.path.exists(os.path.abspath(args[0])):
                  self.no_settings(args[0])
             
      def get_settings_modname(self):
          from django.conf import ENVIRONMENT_VARIABLE

          # get settings module
          settings_modname = None
          if not self.global_settings_path:
              project_path = os.getcwd()

          # ......

      def setup_environ(self, settings_modname):
          from django.core.management import setup_environ

          # setup environ
          # ......

      def no_settings(self, path, import_error=False):
          if import_error:
              error = "Error: Can't find '%s' in your PYTHONPATH.\n" % path

          # .......

      def activate_translation(self):
          from django.conf import settings
          from django.utils import translation
          translation.activate(settings.LANGUAGE_CODE)

      def validate(self):
          """ Validate models. This also ensures that all models are 
          imported in case of import-time side effects."""
          from django.core.management.base import CommandError
          from django.core.management.validation import get_validation_errors
          # ......

      def load(self):
          from django.core.handlers.wsgi import WSGIHandler
         
          self.setup_environ(self.get_settings_modname())
          self.validate()
          self.activate_translation()
          return WSGIHandler()

  # ......

  def run():
    """\
    The ``gunicorn_django`` command line runner for launching Django
    applications.
    """
    from gunicorn.app.djangoapp import DjangoApplication
    DjangoApplication("%prog [OPTIONS] [SETTINGS_PATH]").run()

gunicorn.app.djangoapp:run最终是调用其中的一个函数run()，焦点集中在上述代码的最后两行，创建DjangoApplication后，立刻执行run()。

尽管DjangoApplication定义了不少方法，但注意与WSGIAppliction的骨架一样，实际上就定义了两个方法:

* init()
* load()

最关键的方法run()，估计就是从父类Application里继承而来。
