###############################################################
# Copy's Ecosystem variables. Need to find a list of current tools, hardcoded in the mean time
###############################################################
from System import *

from Deadline.Events import *
from Deadline.Scripting import *

import os
import string

from ecosystem.environment import Environment as eco
#########################################################################################
# This is the function called by Deadline to get an instance of the Draft event listener.
#########################################################################################


def GetDeadlineEventListener():
    return CustomEnvironmentCopyListener()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()

###############################################################
# The event listener class.
###############################################################


class CustomEnvironmentCopyListener (DeadlineEventListener):

    def __init__(self):
        self.OnJobSubmittedCallback += self.OnJobSubmitted

    def Cleanup(self):
        del self.OnJobSubmittedCallback

    def OnJobSubmitted(self, job):
        #stupid hardcoded stuff, will fix soon
        if 'HOUDINI_VERSION' in os.environ: #houdini
            tools = ['houdini%s'%os.environ['HOUDINI_VERSION'], 'htoa%s'%os.environ['HTOA_VERSION']]
        if 'NATRON_VERSION' in os.environ: #natron
            tools = ['natron%s'%os.environ['NATRON_VERSION']]
        self.LogInfo("Ecosystem Tools: %s"%tools)
        env = eco(tools)
        wantedkeys = env.variables.keys()

        self.LogInfo("On Job Submitted Event Plugin: Custom Environment Copy Started")

        for key in wantedkeys:
            self.LogInfo("Setting %s to %s" % (key, os.environ[key]))
            job.SetJobEnvironmentKeyValue(key, os.environ[key])

        RepositoryUtils.SaveJob(job)

        self.LogInfo("On Job Submitted Event Plugin: Custom Environment Copy Finished")
