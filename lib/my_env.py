"""
This module consolidates all local configuration for the script, including modulename collection for logfile name
setup and initializing the config file.
Also other utilities find their home here.
"""

import configparser
import datetime
import logging
import logging.handlers
import os
import platform
import sys


def init_env(projectname, filename):
    """
    This function will initialize the environment: Find and return handle to config file and set-up logging.
    :param projectname: Name that will be used to find ini file in properties subdirectory.
    :param filename: Filename (__file__) of the calling script (for logfile).
    :return: config handle
    """
    projectname = projectname
    modulename = get_modulename(filename)
    config = get_inifile(projectname)
    my_log = init_loghandler(modulename, config["Main"]["logdir"], config["Main"]["loglevel"])
    my_log.info('Start Application')
    return config


def get_inifile(projectname):
    """
    Read Project configuration ini file in subdirectory properties. Config ini filename is the projectname.
    The ini file is located in the properties module, which is sibling of the lib module.
    :param projectname: Name of the project.
    :return: Object reference to the inifile.
    """
    # Use Project Name as ini file.
    # TODO: review procedure to get directory name instead of relative properties/ path.
    if getattr(sys, 'frozen', False):
        # Running Frozen (pyinstaller executable)
        configfile = projectname + ".ini"
    else:
        # Running Live
        # properties directory is sibling of lib directory.
        (filepath_lib, _) = os.path.split(__file__)
        (filepath, _) = os.path.split(filepath_lib)
        # configfile = filepath + "/properties/" + projectname + ".ini"
        configfile = os.path.join(filepath, 'properties', "{p}.ini".format(p=projectname))
    ini_config = configparser.ConfigParser()
    try:
        f = open(configfile)
        ini_config.read_file(f)
        f.close()
    except FileNotFoundError:
        e = sys.exc_info()[1]
        ec = sys.exc_info()[0]
        log_msg = "Read Inifile not successful: %s (%s)"
        print(log_msg % (e, ec))
        sys.exit(1)
    return ini_config


def get_modulename(scriptname):
    """
    Modulename is required for logfile and for properties file.
    :param scriptname: Name of the script for which modulename is required. Use __file__.
    :return: Module Filename from the calling script.
    """
    # Extract calling application name
    (filepath, filename) = os.path.split(scriptname)
    (module, fileext) = os.path.splitext(filename)
    return module


def init_loghandler(scriptname, logdir, loglevel):
    """
    This function initializes the loghandler. Logfilename consists of calling module name + computername.
    Logfile directory is read from the project .ini file.
    Format of the logmessage is specified in basicConfig function.
    This is for Log Handler configuration. If basic log file configuration is required, then use init_logfile.
    Review logger, there seems to be a conflict with the flask logger.
    :param scriptname: Name of the calling module.
    :param logdir: Directory of the logfile.
    :param loglevel: The loglevel for logging.
    :return: logging handler
    """
    modulename = get_modulename(scriptname)
    loglevel = loglevel.upper()
    # Extract Computername
    computername = platform.node()
    # Define logfileName
    logfile = logdir + "/" + modulename + "_" + computername + ".log"
    # Set loglevel for bolt driver to warning
    logging.getLogger("neo4j.bolt").setLevel(logging.WARNING)
    # logging.getLogger("neo4j.http").setLevel(logging.WARNING)
    logging.getLogger("httpstream").setLevel(logging.WARNING)
    # Configure the root logger
    logger = logging.getLogger()
    level = logging.getLevelName(loglevel)
    logger.setLevel(level)
    # Create Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # Create Rotating File Handler
    # Get logfiles of 1M
    maxbytes = 1024 * 1024
    rfh = logging.handlers.RotatingFileHandler(logfile, maxBytes=maxbytes, backupCount=5)
    # Create Formatter for file
    formatter_file = logging.Formatter(fmt='%(asctime)s|%(module)s|%(funcName)s|%(lineno)d|%(levelname)s|%(message)s',
                                       datefmt='%d/%m/%Y|%H:%M:%S')
    formatter_console = logging.Formatter(fmt='%(asctime)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s -'
                                              ' %(message)s',
                                          datefmt='%H:%M:%S')
    # Add Formatter to Console Handler
    ch.setFormatter(formatter_console)
    # Add Formatter to Rotating File Handler
    rfh.setFormatter(formatter_file)
    # Add Handler to the logger
    # logger.addHandler(ch)
    logger.addHandler(rfh)
    return logger


def datestr2date(datestr):
    """
    This method will convert datestring to date type. Datestring must be of the form YYYY-MM-DD
    :param datestr: Datestring to be converted
    :return: Date in datetime object type, or False if not successful
    """
    date_obj = datetime.datetime.strptime(datestr, '%Y-%m-%d').date()
    return date_obj


class LoopInfo:
    """
    This class handles a FOR loop information handling.
    """

    def __init__(self, attribname, triggercnt):
        """
        Initialization of FOR loop information handling. Start message is printed for attribname. Information progress
        message will be printed for every triggercnt iterations.
        :param attribname:
        :param triggercnt:
        :return:
        """
        self.rec_cnt = 0
        self.loop_cnt = 0
        self.attribname = attribname
        self.triggercnt = triggercnt
        curr_time = datetime.datetime.now().strftime("%H:%M:%S")
        print("{0} - Start working on {1}".format(curr_time, str(self.attribname)))
        return

    def info_loop(self):
        """
        Check number of iterations. Print message if number of iterations greater or equal than triggercnt.
        :return:
        """
        self.rec_cnt += 1
        self.loop_cnt += 1
        if self.loop_cnt >= self.triggercnt:
            curr_time = datetime.datetime.now().strftime("%H:%M:%S")
            print("{0} - {1} {2} handled".format(curr_time, str(self.rec_cnt), str(self.attribname)))
            self.loop_cnt = 0
        return

    def end_loop(self):
        curr_time = datetime.datetime.now().strftime("%H:%M:%S")
        print("{0} - {1} {2} handled - End.\n".format(curr_time, str(self.rec_cnt), str(self.attribname)))
        return
