这玩意可以每天给你发一封邮件，提醒你今天用（浙大的）校园卡做了啥交易。

* 0:00 - 3:00 发送的内容是“昨天”的消费记录，3:00 - 23:59 发送的内容是“今天“的消费记录。

- - -

使用了学校出的那个 看起来很不安全的校园卡客户端的 API

原本想用 Google App Engine，结果它的 UrlFetch 不支持非标准 HTTP 端口 sigh

所以才用了 python 2

- - -

要运行它，把它 clone 到顺手的地方，然后建立一个 virtualenv：

`virtualenv venv`

安装需要的 Python 包：

`source ./venv/bin/activate && pip install -r requirements.txt`

创建一个 `localconfig.py` 文件，内容像这样：

```python
# coding: utf-8

config = {
    # 校园卡账号配置
    'student_id': '...',    # 你的学号
    'query_pwd':  '...',    # 你的密码

    # 发件服务器（SMTP with TLS）和收件人配置
    'mail_host': 'smtp.163.com',            # SMTP
    'mail_port': '25',                      # SMTP 端口
    'mail_to':   'another_me@gmail.com',    # 收件人
    'mail_user': 'me@163.com',              # 发件人
    'mail_pass': '...',                     # 发件人密码
}
```

然后运行试试。运气好的话，在 mail_to 配置的邮箱里应该可以收到邮件。

`python main.py`

你可以把它放在服务器上，加一个 crontab，像这样：

```
SHELL=/bin/bash

1 0 * * *  cd ~/workspace/ecard-daily && source ./venv/bin/activate && python ./main.py > cron.log
```

然后就可以 每天记个账辣。
