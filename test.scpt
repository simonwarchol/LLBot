launch application "Messages"
tell application "Messages"
     activate --steal focus

     set targetBuddy to "346637"
     set targetService to id of service "SMS"
     set textMessage to "Just a test"
     set theBuddy to buddy targetBuddy of service id targetService
     send textMessage to theBuddy
end tell