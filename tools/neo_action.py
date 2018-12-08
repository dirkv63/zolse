"""
This script will stop or start a neo4j server.
"""

import argparse
import logging
import os
import subprocess as sp
from lib import my_env

parser = argparse.ArgumentParser(
    description="Start or stop a neo4j server"
)
parser.add_argument('-a', '--action', type=str, required=True, choices=['start', 'stop'],
                    help='Please provide the (start, stop) action.')
args = parser.parse_args()
cfg = my_env.init_env("wolse", __file__)
logging.info("Arguments: {a}".format(a=args))
cmd = os.path.join(cfg["Graph"]["path"], 'bin', cfg["Graph"]["neo4j"])
cmdline = [cmd, args.action, "-verbose"]

module = my_env.get_modulename(__file__)
sof = os.path.join(cfg["Main"]["logdir"], "{mod}_{action}_out.log".format(mod=module, action=args.action))
sef = os.path.join(cfg["Main"]["logdir"], "{mod}_{action}_err.log".format(mod=module, action=args.action))
so = open(sof, "w")
se = open(sef, "w")
logging.info("Command: {c}".format(c=args))
try:
    sp.run(cmdline, stderr=se, stdout=so, check=True)
except sp.CalledProcessError as e:
    logging.error("Some issues during execution, check {sef} and {sof}".format(sof=sof, sef=sef))
else:
    logging.info("No error messages returned, see {sof}!".format(sof=sof))
se.close()
so.close()
