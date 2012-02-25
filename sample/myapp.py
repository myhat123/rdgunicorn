# -*- coding: utf8 -*-

welcome = """
<html>
<head>
  <title>测试</title>
  <style type="text/css">
    h1 { color: red; text-align: center; }
    p { font-size: 22px; text-align: center; }
    .thank { font-size: 24px; color: blue; }
  </style>
</head>
<body>
  <h1>南昌pythoner聚会现场</h1>
  <p>时间: 2012年2月25日 下午14点</p>
  <p>地点: 南昌市红谷滩国际金融中心</p>
  <p class='thank'>感谢: 小幺的挚盟公司大力支持</p>
</body>
</html>
"""

def app(environ, start_response):
    data = welcome
    start_response("200 OK", [
        ("Content-Type", "text/html"),
        ("Content-Length", str(len(data)))
    ])
    return iter([data])

