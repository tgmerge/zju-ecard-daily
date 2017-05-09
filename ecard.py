# coding: utf-8

from base64 import b64encode
import cookielib
import urllib2
import logging
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import jinja2
import traceback

try:
    from localconfig import config
except ImportError:
    logging.exception('Missing localconfig.py')


class Bill(object):
    """一次消费记录"""

    def __init__(self, time_str, amount, balance, place, info):
        """
        @param time_str: str  交易时间，如 2017-05-05 11:13:50
        @param amount: str    交易金额，如 -10.5（消费）或 100（转账）
        @param balance: str   余额
        @param place: str     交易地点
        @param info: str      附加信息 "TRANNAME" + "JDESC"
        """
        self.time_str = time_str
        self.amount = float(amount)
        self.balance = float(balance)
        self.place = place.strip()
        self.info = info.strip()

    def get_time(self):
        """ 以 datetime 对象的形式返回交易时间 """
        return datetime.strptime(self.time_str, r'%Y-%m-%d %H:%M:%S')

    def days_to_today(self):  # -> int
        """
        获取交易发生日到今天的天数。

        @return int     交易发生日到今天的天数。
                        0：今天  1：昨天  2：前天, etc
                None    如果出现错误
        """
        try:
            time_delta = datetime.now().date() - self.get_time().date()
            return time_delta.days
        except Exception:
            logging.exception('Exception on calculating days to today. '
                              'My time_str is %r' % self.time_str)
            return None

    def __repr__(self):
        return 'Bill(time_str=%r, amount=%r, balance=%r, place=%r, info=%r)' %\
            (self.time_str, self.amount, self.balance, self.place, self.info)


class EcardApi(object):

    def __init__(self, sno, pwd):
        """
        校园卡 API。

        @param sno: str    学号
        @param pwd: str    校园卡查询密码
        """

        super(EcardApi, self).__init__()

        self.sno = sno
        self.pwd = pwd

        self.account = ''  # : str 校园卡账号，登录后获取

        self.base_url = 'http://ecardhall.zju.edu.cn:808'

        cookiejar = cookielib.CookieJar()
        self.url_opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(cookiejar),
            urllib2.HTTPSHandler(debuglevel=1))

        logging.debug('Current time: %s' %
                      datetime.now().strftime(r'%Y-%m-%d %H:%M:%S'))

    def login(self):  # --> bool
        """
        登录，在 cookiejar 留下凭据

        @return  True    当登录正常
                 False   当登录失败
        """
        login_url = self.base_url + '/Phone/Login'
        login_data = 'sno=%s&pwd=%s&remember=1&uclass=1&json=true' %\
                     (self.sno, b64encode(self.pwd))
        logging.debug('login: data = %s' % login_data)

        try:
            result = self.url_opener.open(login_url, data=login_data,
                                          timeout=30).read()
            logging.debug('Login request sent, result: %s' % result)
            result_json = json.loads(result)

            if 'IsSucceed' in result_json and result_json['IsSucceed'] is True:
                self.account = str(result_json['Obj'])  # 校园卡账号
                logging.info('Login succeed.')
                return True
            else:
                logging.error('Login failed.')
                return False
        except Exception as err:
            logging.exception('Caught exception during login.')
            return False

    def get_balance(self):  # --> float
        """
        获取账户余额。

        @return  float    当获取余额正常，返回余额（元）
                 None     当出错时
        """
        balance_url = self.base_url + '/User/GetCardAccInfo'
        balance_data = 'acc=&json=true'
        logging.debug('get_balance: data = %s' % balance_data)

        try:
            result = self.url_opener.open(balance_url, data=balance_data,
                                          timeout=30).read()
            logging.debug('Balance request sent, result: %s' % result)
            result_json = json.loads(result)
            result_json = json.loads(result_json['Msg'])
            balance_str = result_json['query_accinfo']['accinfo'][0]['balance']
            balance = float(balance_str)
            logging.debug('Balance = %r' % balance)
            return balance / 100.0
        except Exception as err:
            logging.exception('Caught exception getting balance.')
            return None

    def get_today_bills(self):  # -> (list[Bill], datetime.date)
        """
        获取今天发生的消费。
        只获取接口的第一页（15 次交易），数量应该足够了。
        每天一般不会有 15 次以上的交易……吧

        在 00:00 - 02:59 之间调用，会返回前一天的交易列表；
        在 03:00 - 24:00 之间调用，会返回当天的交易列表。

        @return  list[Bill]     今天的消费列表。每个 Bill 对象是一次消费。
                 datetime       上面这个“今天”是哪一天。
                 如果出现异常，返回 (None, None)
        """
        bills_url = self.base_url + '/Report/GetMyBill'
        bills_data = 'account=%s&page=1&json=true' % self.account
        logging.debug('get_today_bills: data = %s' % bills_data)

        try:
            result = self.url_opener.open(bills_url, data=bills_data,
                                          timeout=30).read()
            logging.debug('Bills request sent, result: %s' % result)
            result_json = json.loads(result)
            result_json = result_json['rows']

            # 交易列表
            bills = []
            # 00:00 - 03:00 之间是前一天；否则是当天
            target_days_to_today = 1 if datetime.now().hour < 3 else 0
            target_date = datetime.today().date() -\
                timedelta(days=target_days_to_today)

            for item in result_json:
                bill = Bill(time_str=item['OCCTIME'],
                            amount=item['TRANAMT'],
                            balance=item['CARDBAL'],
                            place=item['MERCNAME'],
                            info=item['TRANNAME'] + item['JDESC'])
                if bill.days_to_today() == target_days_to_today:
                    bills.append(bill)

            target_date = datetime.today()
            return (bills, target_date)
        except Exception as err:
            logging.exception('Caught exception getting bills.')
            return (None, None)


class SummaryTask(object):
    """ 主要任务 """

    def run(self):
        """ 执行任务 """
        logging.info('Summary task started')

        try:
            balance, bills, target_date = self.gather_info()
            self.make_mail(balance, bills, target_date)
            logging.info('Summary task done.')
        except Exception as err:
            logging.exception('Summary task failed')
            self.make_error_mail(traceback.format_exc())

    def gather_info(self):  # -> tuple[float, list[Bill], datetime.date]
        """
        获取账单信息

        @return  tuple[float, list[Bill], datetime.date]
                       ^余额  ^当天交易列表 ^当天是哪一天
        """
        api = EcardApi(sno=config['student_id'], pwd=config['query_pwd'])
        if not api.login():
            raise RuntimeError('Login failed')

        balance = api.get_balance()
        bills, target_date = api.get_today_bills()

        return (balance, bills, target_date)

    def make_mail(self, balance, bills, target_date):
        """ 制作账单提醒邮件并发送 """
        target_date_str = target_date.strftime(r'%Y-%m-%d')
        time_str = datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')

        template = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))\
                         .get_template('mail_template.html')

        subject = '%s 的校园卡交易情况' % target_date_str
        content = template.render({
            'time': time_str,
            'balance': balance,
            'bills': bills
        })
        logging.debug('Mail subject=%r content=%r' % (subject, content))

        self.send_mail(subject, content)

    def make_error_mail(self, err_string):
        """ 制作错误提示邮件并发送 """
        template = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))\
                         .get_template('mail_error_template.html')

        subject = '今天的校园卡交易情况 - 错误'
        content = template.render({'error': err_string})
        logging.debug('Error mail subject=%r content=%r' % (subject, content))

        self.send_mail(subject, content)

    def send_mail(self, subject, content):
        """
        以 subject 为主题，content 为内容，使用 localconfig.config 中的配置
        发送一封邮件
        """
        mail_host = config['mail_host']
        mail_port = config['mail_port']
        mail_to = config['mail_to']
        mail_user = config['mail_user']
        mail_pass = config['mail_pass']

        msg = MIMEText(content.encode('utf-8'), 'html', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = mail_user
        msg['To'] = mail_to

        try:
            server = smtplib.SMTP(mail_host, mail_port)
            server.ehlo()
            server.starttls()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, mail_to, msg.as_string())
            server.close()
            logging.info('Mail sent!')
        except Exception as e:
            logging.exception('Failed to send mail.')
