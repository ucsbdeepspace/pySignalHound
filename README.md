pySignalHound
=============

A python wrapper for the Test Equipment Plus SignalHound series of spectrum analyzers.


The primary file is "SignalHound.py". It defines one class, "SignalHound()", that currently can only open the first signal-hound analyser it finds.

Predominantly, all C API errors should be caught, and re-raised as python exceptions with helpful error messages.

Also, there is *some* error checking for function parameters. I should probably go through and add `{dll}.{function}.restype = {something}` type hints to all the function calls, but I think the fact that I'm explicitly casting all parameters to ctypes values should somewhat ameliorate that need.

At the moment, the one function that takes a callback (`bbStartRawSweepLoop`) properly wraps a passed python function, so it gets called via the C callback,
though it still relys on the user decoding the C function call arguments. I want to do something about that in the near future.



* ----------------------------------------------------------------------------
* "THE BEER-WARE LICENSE":
* Connor Wolf <wolf@imaginaryindustries.com> wrote this file. As long as you retain
* this notice you can do whatever you want with this stuff. If we meet some day,
* and you think this stuff is worth it, you can buy me a beer in return.
* (Only I don't drink, so a soda will do). Connor
* Also, support the Signal-Hound devs. Their hardware is pretty damn awesome.
* ----------------------------------------------------------------------------
