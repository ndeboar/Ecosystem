from System import *
from System.IO import *
from System.Diagnostics import *
from System.Text.RegularExpressions import *

from Deadline.Plugins import *
from Deadline.Scripting import *

import os

def GetDeadlinePlugin():
    return NatronPlugin()
    
def CleanupDeadlinePlugin( deadlinePlugin ):
    deadlinePlugin.Cleanup()
    
class NatronPlugin(DeadlinePlugin):
    Progress = 0
    CurrFrame = 0
    Version = -1.0
    TempProjectFilename = ""

    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
        self.PreRenderTasksCallback += self.PreRenderTasks
        self.PostRenderTasksCallback += self.PostRenderTasks
    
    def Cleanup(self):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback
        
        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
        del self.PreRenderTasksCallback
        del self.PostRenderTasksCallback

    ## Called by Deadline to initialize the process.
    def InitializeProcess(self):
        # Set the plugin specific settings.
        self.SingleFramesOnly = True
        self.StdoutHandling = True

        # Set the stdout handlers.
        self.AddStdoutHandlerCallback(".*Rendering started.*").HandleCallback += self.HandleStdoutStarted
        self.AddStdoutHandlerCallback(".*Frame rendered: ([0-9]*).*").HandleCallback += self.HandleStdoutProgress
        self.AddStdoutHandlerCallback(".*Rendering finished.*").HandleCallback += self.HandleStdoutCompleted
        self.AddStdoutHandlerCallback(".*ERROR:.*").HandleCallback += self.HandleStdoutError

    def RenderExecutable(self):
        # Get the version we're rendering with.
        self.Version = float( self.GetPluginInfoEntry( "Version" ) )
        build = self.GetPluginInfoEntryWithDefault( "Build", "None" ).lower()

        # We support minor versions, so we should default to the *.0 version if the *.x version they're using isn't supported yet.
        versionNotSupported = "this version is not supported yet"
        natronExeList = self.GetConfigEntryWithDefault( "RenderExecutable" + str(self.Version).replace( ".", "_" ), versionNotSupported )
        if natronExeList == versionNotSupported:
            oldVersion = self.Version
            self.Version = float(int(self.Version))

            natronExeList = self.GetConfigEntryWithDefault( "RenderExecutable" + str(self.Version).replace( ".", "_" ), versionNotSupported )
            if natronExeList == versionNotSupported:
                self.FailRender( "Natron major version " + str(int(self.Version)) + " is currently not supported." )
            else:
                self.LogWarning( "Natron minor version " + str(oldVersion) + " is currently not supported, so version " + str(self.Version) + " will be used instead." )
        
        executable = ""
        if(SystemUtils.IsRunningOnWindows()):
            if( build == "32bit" ):
                self.LogInfo( "Enforcing 32 bit build of Natron" )
                executable = FileUtils.SearchFileListFor32Bit( natronExeList )
                if( executable == "" ):
                    self.LogWarning( "32 bit Natron render executable was not found in the semicolon separated list \"" + natronExeList + "\". Checking for any executable that exists instead." )        
            elif( build == "64bit" ):
                self.LogInfo( "Enforcing 64 bit build of Natron" )
                executable = FileUtils.SearchFileListFor64Bit( natronExeList )
                if( executable == "" ):
                    self.LogWarning( "64 bit Natron render executable was not found in the semicolon separated list \"" + natronExeList + "\". Checking for any executable that exists instead." )
            
        if( executable == "" ):
            self.LogInfo( "Not enforcing a build of Natron" )
            executable = FileUtils.SearchFileList( natronExeList )
            if executable == "":
                self.FailRender( "Natron render executable was not found in the semicolon separated list \"" + natronExeList + "\". The path to the render executable can be configured from the Plugin Configuration in the Deadline Monitor." )

        return executable

    def RenderArgument(self):
        renderArgs = ""

        writerNodeName = self.GetPluginInfoEntryWithDefault( "WriterNodeName", "" )

        if writerNodeName != "":
            renderArgs += "-w %s" % writerNodeName

            startFrame = str(self.GetStartFrame())
            endFrame = str(self.GetEndFrame())

            if startFrame != 0 and endFrame != 0:
                renderArgs += " %s-%s" % ( startFrame, endFrame ) 
            renderArgs += " \"" + self.TempProjectFilename + "\""
        else:
            renderArgs += "\"" + self.TempProjectFilename + "\""

        return renderArgs

    def PreRenderTasks(self):
        self.LogInfo( "Starting Natron Task..." )

        projectFilename = self.GetPluginInfoEntryWithDefault( "ProjectFile", self.GetDataFilename() )
        projectFilename = RepositoryUtils.CheckPathMapping( projectFilename )
        projectFilename = PathUtils.ToPlatformIndependentPath( projectFilename )
        
        # Check if we should be doing path mapping.
        if self.GetBooleanConfigEntryWithDefault( "EnablePathMapping", True ):
            self.LogInfo( "Performing path mapping on Natron project file" )
            
            tempProjectDirectory = self.CreateTempDirectory( "thread" + str(self.GetThreadNumber()) )
            tempProjectFileName = Path.GetFileName( projectFilename )
            self.TempProjectFilename = Path.Combine( tempProjectDirectory, tempProjectFileName )
            
            RepositoryUtils.CheckPathMappingInFile( projectFilename, self.TempProjectFilename )
            if SystemUtils.IsRunningOnLinux() or SystemUtils.IsRunningOnMac():
                os.chmod( self.TempProjectFilename, os.stat( projectFilename ).st_mode )
        else:
            self.TempProjectFilename = projectFilename
                
        self.TempProjectFilename = PathUtils.ToPlatformIndependentPath( self.TempProjectFilename )

    def PostRenderTasks(self):
        # Clean up the temp file if we did path mapping on the natron project file.
        if self.GetBooleanConfigEntryWithDefault( "EnablePathMapping", True ):
            try:
                File.Delete( self.TempProjectFilename )
                self.LogInfo( "Deleted Natron Temp Project File: %s" % self.TempProjectFilename )
            except:
                self.LogWarning( "Failed to delete Natron Temp Project File: %s" % self.TempProjectFilename )

        self.LogInfo( "Finished Natron Task." )

    def HandleStdoutStarted( self ):
        msg = self.GetRegexMatch( 0 )
        self.SetStatusMessage( msg )
        self.SetProgress( 0.0 )

    def HandleStdoutProgress( self ):
        self.CurrFrame = float( self.GetRegexMatch(1) )
        self.SetStatusMessage( "Frame rendered: " + self.GetRegexMatch(1) )

        if((self.GetStartFrame() - self.GetEndFrame()) == 0):
            self.SetProgress( self.Progress )
        else:
            self.SetProgress((((1.0 / ( self.GetEndFrame() - self.GetStartFrame() + 1 ) )) * self.Progress ) + (((( self.CurrFrame - self.GetStartFrame() ) * 1.0 ) / ((( self.GetEndFrame() - self.GetStartFrame() + 1 ) * 1.0 ))) * 100))

    def HandleStdoutCompleted( self ):
        msg = self.GetRegexMatch( 0 )
        self.SetStatusMessage( msg )
        self.SetProgress( 100.0 )       

    def HandleStdoutError(self):
        self.SetStatusMessage( "" )
        self.SetProgress( 0.0 )
        self.FailRender( self.GetRegexMatch(0) )
