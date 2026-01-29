---
name: example-hook
emoji: 🎯
events:
  - command:example
  - session:example
description: An example hook demonstrating the hook system
requires:
  bins: []
  env: []
  python_packages: []
enabled: true
priority: 100
---

# Example Hook

This is an example hook that demonstrates how to create custom hooks for LurkBot.

## Features

- Listens to `command:example` and `session:example` events
- Logs event information
- Adds messages to the event

## Usage

Place this hook directory in one of the following locations:
1. `<workspace>/hooks/` (highest priority)
2. `~/.lurkbot/hooks/` (user-level)
3. Built-in hooks (bundled with LurkBot)

The hook will be automatically discovered and loaded when the system starts.
