#!/bin/sh
# Headless Blender with its own user folder. Without BLENDER_USER_RESOURCES, `--factory-startup` treats every
# extension wheel in the shared user folder as unused and deletes it (2026-11-12: it removed the packages of the
# Blender MCP bridge that another session was using). Usage: ./blender_headless.sh script.py -- args...
export BLENDER_USER_RESOURCES="${BLENDER_USER_RESOURCES:-$LOCALAPPDATA/Temp/claude/blender_headless_user}"
mkdir -p "$BLENDER_USER_RESOURCES"
exec "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python "$@"
