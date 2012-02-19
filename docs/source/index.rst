.. RDGUNICORN documentation master file, created by
   sphinx-quickstart on Mon Jan 30 16:12:46 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

阅读gunicorn代码文档
====================

说明
----

因为在玩heroku app时，heroku给出的教程中，采用了gunicorn来部署应用；在南昌echo提出用freebsd的kqueue改造flup时，我建议可以对比一下gunicorn。但自己仅仅是在heroku上小用了一把而已，并没有深入研究，为了此次南昌 pythoner 2012年第一次聚会，特意浏览了一下gunicorn的代码，感觉上gunicorn代码写得比较小巧精炼，整理出来，算是抛砖引玉。

文档内容
--------

.. toctree::
   :maxdepth: 3

   intro.rst
   design.rst
   getstart.rst
   readstart.rst
   app_base.rst
   config.rst
   arbiter.rst
   route.rst
   http.rst
   play.rst


索引表
======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

