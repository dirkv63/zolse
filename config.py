import os
# Be careful: Variable names need to be UPPERCASE


class Config(object):
    SECRET_KEY = os.urandom(24)
    LOGDIR = os.environ.get("LOGDIR")
    LOGLEVEL = os.environ.get("LOGLEVEL")
    NEO4J_USER = os.environ.get("NEO4J_USER")
    NEO4J_PWD = os.environ.get("NEO4J_PWD")
    NEO4J_DB = os.environ.get("NEO4J_DB")
    if os.environ.get("WTF_CSR_ENABLED"):
        WTF_CSRF_ENABLED = os.environ.get("WTF_CSR_ENABLED")
