pySignalHound
=============

A python wrapper for the Test Equipment Plus SignalHound series of spectrum analyzers.


The primary file is "SignalHound.py". It defines one class, "SignalHound()", that currently can only open the first signal-hound analyser it finds.

Predominantly, all C API errors should be caught, and re-raised as python exceptions with helpful error messages.

Also, there is *some* error checking for function parameters. I should probably go through and add `{dll}.{function}.restype = {something}` type hints to all the function calls, but I think the fact that I'm explicitly casting all parameters to ctypes values should somewhat ameliorate that need.

At the moment, the one function that takes a callback (`bbStartRawSweepLoop`) properly wraps a passed python function, so it gets called via the C callback,
though it still relys on the user decoding the C function call arguments. I want to do something about that in the near future.



---

The primary API file is `SignalHound.py`.

`bb_api_h.py` is a transliteration of the bb_api.h file from the C api, and primarily defines most of the configuration constants used for controlling the SignalHound. It contains no executable code.

`tests.py` contains a number of different hardware test facilities.

`tests.py` is a good proof-of-concept demo. It's currently messy, but it shows the capabilities of both python and the SignalHound.

 - `python test.py radio` will do real-time software decoding and playback of FM radio.
 - `python test.py raw-pipe` will log the full-rate 160 MBPS data-stream to disk in real-time (requires a SSD).
 - `python test.py callback` demonstrates the ability to have the C api callback into pure python code

 Utilities:
 - `python test.py status` prints the connected hardware version, serial, firmware version, and API version, as well as querying the hardware diagnostics values.
 - `python test.py reset` triggers a firmware-level reset of the hardware, equivalent to disconnecting and reconnecting the USB interface.

While `tests.py` is functional, it's very messily written. Cleanup is needed. The API files themselves are fairly coherent, however.
The ability to configure some of the test-modes is also a good idea, though it also needs to be implemented.

---


* ----------------------------------------------------------------------------
* "THE BEER-WARE LICENSE":
* Connor Wolf <wolf@imaginaryindustries.com> wrote this file. As long as you retain
* this notice you can do whatever you want with this stuff. If we meet some day,
* and you think this stuff is worth it, you can buy me a beer in return.
* (Only I don't drink, so a soda will do). Connor
* Also, support the Signal-Hound devs. Their hardware is pretty damn awesome.
* ----------------------------------------------------------------------------
