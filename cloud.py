# coding: utf-8

import logging
import webapp2

from ecard import SummaryTask as Task


class PingPage(webapp2.RequestHandler):
    def get(self):
        logging.info('Ping -> pong')
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('pong')


class SummaryTask(webapp2.RequestHandler):
    def get(self):
        task = Task()
        task.run()


routes = [
    (r'/ping', PingPage),
    (r'/tasks/summary', SummaryTask)
]

config = {
}

app = webapp2.WSGIApplication(routes=routes, debug=True, config=config)


if __name__ == '__main__':
    """ Run standalong server for testing """
    logging.getLogger().setLevel(logging.DEBUG)
    from paste import httpserver, reloader
    reloader.install()
    httpserver.serve(app, host='127.0.0.1', port='8080')
