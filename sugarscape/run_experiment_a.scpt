tell application "NetLogo 7.0.3"
	activate
end tell

delay 2

tell application "System Events"
	tell process "NetLogo 7.0.3"
		-- Click setup button
		click button "setup" of window 1
		delay 1

		-- Click go button to start
		click button "go" of window 1

		-- Wait for simulation to complete (this is approximate)
		delay 300

		-- Click go button again to stop
		click button "go" of window 1
	end tell
end tell
