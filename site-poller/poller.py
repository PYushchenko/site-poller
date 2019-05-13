import argparse
import signal
import threading
import time
import urllib.request
from datetime import timedelta
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

WAIT_TIME_SECONDS = 1

CONFIGFILE = '.sitepoller'


class ProgramKilled(Exception):
    pass


def poll_site(url, *args, **kwargs):
    print(time.ctime())
    print(url)

    with urllib.request.urlopen(url) as response:
        return str(response.read())


def send_email(url):
    msg = MIMEText("Site changes detected for url " + url)
    msg["From"] = "****"
    msg["To"] = "****"
    msg["Subject"] = "Site changes detected."
    p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
    p.communicate(msg.as_bytes())


def signal_handler(signum, frame):
    raise ProgramKilled


class Job(threading.Thread):
    def __init__(self, interval, execute, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = False
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = execute
        self.args = args
        self.kwargs = kwargs
        self.html = ""

        print(self.kwargs)

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        print("run")
        while not self.stopped.wait(self.interval.total_seconds()):
            tmp = self.execute(*self.args, **self.kwargs)
            if tmp != self.html:
                print("Changes detected")
                send_email(**self.kwargs)
                self.html = tmp


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description='Polls site for changes.')
    parser.add_argument('url', metavar='URL', type=str, help='url to poll for changes')
    pargs = parser.parse_args()
    print(pargs)

    job = Job(interval=timedelta(seconds=WAIT_TIME_SECONDS), execute=poll_site, **vars(pargs))
    job.start()

    while True:
        try:
            time.sleep(1)
        except ProgramKilled:
            print
            "Program killed: running cleanup code"
            job.stop()
            break