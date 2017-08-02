# RememberScript

## Introduction

This is a Python 3.6 library for creating chat bot finite state machines (FSM).  The library is fully compatible, and meant to be used with, asyncio.  YAML documents are used for creating scripts, accompanied by optional Python source code for defining state variables and related functionality.

## Requirements
  * Python >3.6
  * Libraries in requirements.txt

## Why / Inspiration
This library was/is being built for a personal Python bot project. Before settling on building something new I evaluated existing solutions such as RiveScript and ChatScript. However, I came to the conclusion that a few things were missing:

  * More control / flexibility -> better to use the FSM abstraction as a superset but allow for RiveScript-like syntax by leaving out state attributes (like names)
  * Using arbitrary Python functions in triggers
  * Allow trigger weights to be set programmatically based on the message
  * Python asyncio compatibility
  * Timed/Periodic triggers
  * Multiple replies per message
  * Asyncronous replies to a message, e.g. progress update on a task the bot is
    performing
  * A context stack for getting back to previous stories and states

To fix these I set out to build this library for Python. The philosophy is to keep things as simple as possible and use existing technology before inventing anything new. Therefore this project uses:

  * YAML for defining scripts [instead of using a homegrown interpreted language]
  * Regex for matching in triggers [^]
  * Python 'exec' and 'eval' expressions in the triggers and actions [^]

The end result is hopefully a small and simple library that's easy to
understand and modify.

### Why Python 3.6, asyncio
Python >3.6 allows for using the new async syntax for coroutines as well as type hinting (from 3.5).

## Examples
examples here
