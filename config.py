import os
# Be careful: Variable names need to be UPPERCASE


class Config(object):
    SECRET_KEY = os.urandom(24)
    LOGDIR = os.environ["LOGDIR"]
    LOGLEVEL = os.environ["LOGLEVEL"]
    NEO4J_USER = os.environ["NEO4J_USER"]
    NEO4J_PWD = os.environ["NEO4J_PWD"]
    NEO4J_DB = os.environ["NEO4J_DB"]
    if os.environ.get("WTF_CSR_ENABLED"):
        WTF_CSRF_ENABLED = os.environ["WTF_CSR_ENABLED"]
    if os.environ.get["SERVER_NAME"]:
        SERVER_NAME = os.environ["SERVER_NAME"]
