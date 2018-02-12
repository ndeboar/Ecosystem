# Houdini.py
A replacment for \\DeadlineRepository10\plugins\Houdini\Houdini.py

The function RenderExecutable now looks to the HOUDINI_LOCATION env var for the location of Houdini; bypassing the UI. 

# CustomEnvironmentCopy
Add to the Deadline events directory.
Currently just sets the environment variables for Houdini and HtoA that are defined by Ecosystem, and passes them onto Deadline. 
