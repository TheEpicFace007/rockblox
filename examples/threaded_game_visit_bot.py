from threading import Thread
import rockblox
import requests
import time

place_id = 1818
workers = 5

with open("cookies.txt", encoding="UTF-8", errors="ignore") as f:
    cookies = [
        max(line.replace("WARNING:", "").split(":"), key=len)
        for line in set(f.read().splitlines())
    ]

class Worker(Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        while 1:
            session = self.get_session()

            try:
                with rockblox.Client(session, place_id) as client:
                    time.sleep(1)
                    client.wait_for(10)
                print("Visited using", session.name)
            except Exception as err:
                print("err with", session.name, err)
    
    def get_session(self):
        while 1:
            cookie = cookies.pop(0)
            try:
                session = rockblox.Session(cookie)
                cookies.append(cookie)
                return session

            except requests.exceptions.RequestException:
                cookies.append(cookie)

            except rockblox.WebError as err:
                if err.type() == rockblox.WebErrorType.UNAUTHENTICATED:
                    continue
                else:
                    cookies.append(cookie)

mutex = rockblox.ClientMutex()
for _ in range(workers):
    Worker().start()