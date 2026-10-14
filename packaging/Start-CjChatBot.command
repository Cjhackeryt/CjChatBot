#!/bin/bash
cd "$(dirname "$0")"

if [ ! -x "./CjChatBot" ]; then
    echo "CjChatBot executable is missing. Extract the complete CjChatBot folder first."
    read -r -p "Press Return to close this window..."
    exit 1
fi

echo "Starting CjChatBot. Keep this Terminal window open while you use the app."
./CjChatBot
status=$?

if [ "$status" -ne 0 ]; then
    echo
    echo "CjChatBot exited with an error."
    echo "If available, startup details are in ~/Library/Application Support/CjChatBot/startup-error.log"
    read -r -p "Press Return to close this window..."
fi

exit "$status"
