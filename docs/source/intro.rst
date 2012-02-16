****
介绍  
****

什么是gunicorn
==============

gunicorn，是“Green Unicorn"，脱胎于ruby社区的Unicorn，移植到python上，成为一个WSGI HTTP Server，WSGI是"Web Server Gateway Interface"，是python的web接口规范。

gunicorn的特性
==============

* 支持 Django，paster，wsgi程序
* 非常容易配置（相比较而言）
* 自动管理多个worker进程
* 可以采用不同的后台扩展接口（sync, gevent, tornado等）
