********
配置参数
********

初始化流程主要解决的是加载配置参数或文件，重点部分在load_config()方法中。

配置参数的处理主要是在config.py文件中，有三个主要的类:

* Config
* Setting
* SettingMeta

先挑有趣的代码开始阅读。

.. code-block:: python

  class Setting(object):
    __metaclass__ = SettingMeta

  class SettingMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(SettingMeta, cls).__new__

元类编程
========

SettingMeta和Setting继承的方式，是完全不同的，尽管他们都是用class来定义。

__metaclass__ = SettingMeta

metaclass是元类，它是一个类的类（型）。相对于类可以在运行时动态构造对象而言，元类也可以在运行时动态生成类。

解释type
--------

示例::

  >>> type('abc')
  <type 'str'>
  >>> type('abc')('def')
  'def'
  >>> type(type(1))
  <type 'type'>
  >>> type(type(1))(1)
  <type 'int'>

  >>> Calculator = type('Calculator', (), {'add': lambda self, x, y: x+y, 'sub': lambda sef, x, y: x-y })
  >>> calc = Calculator()
  >>> type(calc)
  <class '__main__.Calculator'>
  >>> 
  >>> print calc.add(1, 2)
  3
  >>> print calc.sub(1, 2)
  -1

type实际上是接收3个参数，第一个参数是类名，第二个是父类（由于允许多重继承，所以是个元组，空元组表示父类为object），第三个参数为类的成员字典。它会返回一个新风格的type对象，这个对象实际上就是一个动态生成的类。

跟踪子类
--------

下面的内容是摘自pro django一书中的内容，是自己在2009-03-31翻译的，放在博客上，从中可以很清楚的知道元类的使用方式。

考虑一个应用，在任何时候，访问一个特定类的所有子类列表。metaclass是一个非常好的处理手段，但是存在一个问题。记住，每一个带有__metaclass__属性的类都要处理，包括新的基类，他们是不需要被注册的（只有它的子类要被注册）。

要处理好这个问题，就要作些额外的处理，但这样作也是很直接了当的，同时也是很有益处的。

示例::

  >>> class SubclassTracker(type):
  ...     def __init__(cls, name, bases, attrs):
  ...         try:
  ...             if TrackedClass not in bases:
  ...                 return
  ...         except NameError:
  ...             return
  ...         TrackedClass._registry.append(cls)
  ...
  >>> class TrackedClass(object):
  ...     __metaclass__ = SubclassTracker
  ...     _registry = []
  ...
  >>> class ClassOne(TrackedClass):
  ...     pass
  ...
  >>> TrackedClass._registry
  [<class '__main__.ClassOne'>]
  >>> class ClassTwo(TrackedClass):
  ...     pass
  ...
  >>> TrackedClass._registry
  [<class '__main__.ClassOne'>, <class '__main__.ClassTwo'>]

这个metaclass执行了两个功能。首先，try块确保父类，TrackedClass，已经定义好了。如果没有的话，就抛出NameError异常， 这个过程就表明metaclass当前正处理TrackedClass。TrackedClass那还能处理更多的东西，但是这个例子为了简单，忽略掉了，只要通过注册就行了。

...

所有TrackedClass的子类能在任何时候从注册表中提取。 TrackedClass的任何子类都将出现在这个注册表中，不管子类在哪里定义的。执行这个类定义的过程就开始注册它，应用程序能导入任何有这些类和 metaclass的模块。

gunicorn配置怎么处理
====================

Setting、SettingMeta与TrackedClass、SubclassTracker主体上是一致的

.. code-block:: python
  :linenos:

  class SettingMeta(type):
      def __new__(cls, name, bases, attrs):
          super_new = super(SettingMeta, cls).__new__
          parents = [b for b in bases if isinstance(b, SettingMeta)]
          if not parents:
              return super_new(cls, name, bases, attrs)
      
          attrs["order"] = len(KNOWN_SETTINGS)
          attrs["validator"] = wrap_method(attrs["validator"])
          
          new_class = super_new(cls, name, bases, attrs)
          new_class.fmt_desc(attrs.get("desc", ""))
          KNOWN_SETTINGS.append(new_class)
          return new_class

      def fmt_desc(cls, desc):
          desc = textwrap.dedent(desc).strip()
          setattr(cls, "desc", desc)
          setattr(cls, "short", desc.splitlines()[0])

.. code-block:: python
  :linenos:

  class Setting(object):
      __metaclass__ = SettingMeta
      
      name = None
      value = None
      section = None
      cli = None
      validator = None
      type = None
      meta = None
      action = None
      default = None
      short = None
      desc = None
      
      def __init__(self):
          if self.default is not None:
              self.set(self.default)    
          
      def add_option(self, parser):
          if not self.cli:
              return
          args = tuple(self.cli)
          kwargs = {
              "dest": self.name,
              "metavar": self.meta or None,
              "action": self.action or "store",
              "type": self.type or "string",
              "default": None,
              "help": "%s [%s]" % (self.short, self.default)
          }
          if kwargs["action"] != "store":
              kwargs.pop("type")
          parser.add_option(*args, **kwargs)
      
      def copy(self):
          return copy.copy(self)
      
      def get(self):
          return self.value
      
      def set(self, val):
          assert callable(self.validator), "Invalid validator: %s" % self.name
          self.value = self.validator(val)

.. code-block:: python
  :linenos:

  class Bind(Setting):
      name = "bind"
      section = "Server Socket"
      cli = ["-b", "--bind"]
      meta = "ADDRESS"
      validator = validate_string
      default = "127.0.0.1:8000"
      desc = """\
          The socket to bind.
          
          A string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'. An IP is a valid
          HOST.
          """

  class Workers(Setting):
      name = "workers"
      section = "Worker Processes"
      cli = ["-w", "--workers"]
      meta = "INT"
      validator = validate_pos_int
      type = "int"
      default = 1
      desc = """\
          The number of worker process for handling requests.
          
          A positive integer generally in the 2-4 x $(NUM_CORES) range. You'll
          want to vary this a bit to find the best for your particular
          application's work load.
          """          

注意在SettingMeta中的KNOWN_SETTINGS.append(new_class)，和TrackedClass._registry，Bind、Workers在声明时，就已经执行SettingMeta的__new__()，留意__new__()与__init__()的区别
  
  >>> from gunicorn import config
  >>> b = config.Bind()
  >>> b.default
  '127.0.0.1:8000'
  >>> b.cli
  ['-b', '--bind']
  >>> b.desc
  "The socket to bind.\n\nA string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'. An IP is a valid\nHOST."
  >>> b.name
  'bind'
  >>> b.value
  '127.0.0.1:8000'
  >>> b.validator
  <bound method Bind._wrapped of <gunicorn.config.Bind object at 0x8eb4eec>>
  >>> b.order
  1

SettingMeta中第8-9行，动态生成的有：validator()方法与order属性，在导入config时就已完成。

.. code-block:: python
  :linenos:

  def wrap_method(func):
      def _wrapped(instance, *args, **kwargs):
          return func(*args, **kwargs)
      return _wrapped

这里使用了python decorator的特性，wrap_method('validate_string')通过这样处理后，把validate_string替换成新的名称validator。
  
  >>> from gunicorn import config
  >>> c = config.Config()
  >>> c.address
  ('127.0.0.1', 8000)
  >>> c.workers
  1
  >>> c.worker_class
  <class 'gunicorn.workers.sync.SyncWorker'>

由Config中的parser方法，来解析命令行的参数
