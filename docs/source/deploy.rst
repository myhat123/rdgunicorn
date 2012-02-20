********
部署应用
********

gunicorn官方主站强烈推荐nginx作为web server proxy，同时给出建议：如果选择其他的web server，在使用gunicorn的sync worker时，就需要确保它能缓冲慢速客户端的请求。没有这个缓冲的功能，gunicorn很容易遭受dos的攻击。可以用slowloris测试一下，看看你的web server proxy的响应如何。

slowloris是什么? 瞧瞧去::

  http://ha.ckers.org/slowloris/

slowloris，采用perl编写的一个脚本，有趣有趣。

转回正题，看看下面是nginx的配置示例，在nginx.conf中http部分加入::

  upstream app_server {
      server http://localhost:8000 fail_timeout=0;
  }

在sites-available目录下的default中::

  server {
      listen 80 default;
      client_max_body_size 4G;
      server_name _;

      keepalive_timeout 5;

      location / {
          # checks for static file, if not found proxy to app
          try_files $uri @proxy_to_app;
      }

      location @proxy_to_app {
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header Host $http_host;
          proxy_redirect off;

          proxy_pass   http://app_server;
      }
  }

在浏览器中输入::
  
  http://localhost

即可得到输出结果
