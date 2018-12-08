"""
This script will take a backup of the neo4j database.
"""

import logging
import os
import subprocess as sp
from lib import my_env

cfg = my_env.init_env("wolse", __file__)
db = cfg["Graph"]["db"]

# Remove transaction log files first to avoid false changes
dbdir = os.path.join(cfg["Graph"]["path"], "data/databases", db)
filelist = [file for file in os.listdir(dbdir) if 'transaction' in file]
for file in filelist:
        ffn = os.path.join(dbdir, file)
        os.remove(ffn)
        logging.info("Remove file {ffn}".format(ffn=ffn))

# Remove previous dump file if it still exists
dbname = db.split(".")[0]
dumpname = "{dbname}.dump".format(dbname=dbname)
dumpffp = os.path.join(cfg["Graph"]["dumpdir"], dumpname)
if os.path.isfile(dumpffp):
    os.remove(dumpffp)
# Define Standard Out and Standard Error file for command
module = my_env.get_modulename(__file__)
sof = os.path.join(cfg["Main"]["logdir"], "{mod}_out.log".format(mod=module))
sef = os.path.join(cfg["Main"]["logdir"], "{mod}_err.log".format(mod=module))
so = open(sof, "w")
se = open(sef, "w")
# Define and execute command
cmd = os.path.join(cfg["Graph"]["path"], 'bin', cfg["Graph"]["adm"])
args = [cmd, "dump", "--database={db}".format(db=db), "--to={dumpffp}".format(dumpffp=dumpffp)]
logging.info("Command: {c}".format(c=args))
try:
    sp.run(args, stderr=se, stdout=so, check=True)
except sp.CalledProcessError as e:
    logging.error("Some issues during execution, check {sef} and {sof}".format(sof=sof, sef=sef))
else:
    logging.info("No error messages returned, see {sof}!".format(sof=sof))
se.close()
so.close()
