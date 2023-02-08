
from .phew import logging
import random, os, re, time
import uasyncio  # type: ignore comment;

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVXYZ0123456789"
SesKeyLen = 8
SessionTime = 30*60             # in seconds
SessionAutoRefresh = False      # true is not yet implemented
SERVER_SESSIONS = []

#RandomSessionID : {"ExpiresOn": "timestamp", "data":{}}

# make randomizer be random
random.seed(os.urandom(32)[0] % (1 << 32))

def generate_random_string(length, alphabet=ALPHABET):
    return ''.join(random.choice(alphabet) for i in range(length))


async def clear_ended():
    global SERVER_SESSIONS
    while True:
        sesToRemove = []
        for ses in SERVER_SESSIONS:
            if ses[1] < time.time():
                sesToRemove.append(ses[0])
        if (len(sesToRemove)>0):
            logging.info(f"> {len(sesToRemove)} expired sessions deleted")
            tempSes = []
            for ses in SERVER_SESSIONS:
                if ses[0] not in sesToRemove:
                    tempSes.append(ses)
            SERVER_SESSIONS = tempSes

        await uasyncio.sleep(60)


def create(ip, data={}):
    global SERVER_SESSIONS
    sesKey = generate_random_string(SesKeyLen)
    SERVER_SESSIONS.append([sesKey, time.time() + SessionTime, ip, data])
    return sesKey


def exist(sesKey):
    global SERVER_SESSIONS
    for ses in SERVER_SESSIONS:
        if ses[0] == sesKey:
            return True
    return False


def is_valid(sesKey):
    global SERVER_SESSIONS
    for ses in SERVER_SESSIONS:
        if ses[0] == sesKey and ses[1] > time.time():
            return True
    return False


def get_data(sesKey):
    global SERVER_SESSIONS
    if is_valid(sesKey):
        for ses in SERVER_SESSIONS:
            if ses[0] == sesKey:
                return ses[3]
    return False


def refresh_session(sesKey, ignore_time=False):
    global SERVER_SESSIONS
    sessions = []
    if exist(sesKey) and (is_valid(sesKey) or ignore_time):
        for ses in SERVER_SESSIONS:
            if ses[0] == sesKey:
                sessions.append([sesKey, time.time() + SessionTime, ses[2], ses[3]])
            else:
                sessions.append(ses)
        SERVER_SESSIONS = sessions


def extractFromCookie(request):
    # match between "PhewSession=" and ; or ' or end of string
    try:
        m = re.search(r'PhewSession=(.*?)(;|\'|$)', request.headers.get("cookie"))
        if m:
            return m.group(1)
    except TypeError:  # type: ignore comment;
        return None