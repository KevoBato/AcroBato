#!/usr/bin/env python3
"""List the joysticks SDL2 exposes (name, GUID, path, buttons/axes), using a given libSDL2.
Usage: sdl-joysticks.py <libSDL2-2.0.so.0>   (set SDL_* hints via environment to compare)"""
import ctypes
import sys
import time

sdl = ctypes.CDLL(sys.argv[1])
SDL_INIT_JOYSTICK = 0x200
sdl.SDL_JoystickNameForIndex.restype = ctypes.c_char_p
sdl.SDL_JoystickPathForIndex.restype = ctypes.c_char_p
sdl.SDL_JoystickOpen.restype = ctypes.c_void_p


class GUID(ctypes.Structure):
    _fields_ = [('data', ctypes.c_uint8 * 16)]


sdl.SDL_JoystickGetDeviceGUID.restype = GUID
sdl.SDL_JoystickGetDeviceVendor.restype = ctypes.c_uint16
sdl.SDL_JoystickGetDeviceProduct.restype = ctypes.c_uint16
for f in ('SDL_JoystickNumButtons', 'SDL_JoystickNumAxes', 'SDL_JoystickNumHats'):
    getattr(sdl, f).argtypes = [ctypes.c_void_p]

if sdl.SDL_Init(SDL_INIT_JOYSTICK) != 0:
    sys.exit('SDL_Init failed')
time.sleep(1.5)  # let HIDAPI devices appear
sdl.SDL_JoystickUpdate()
n = sdl.SDL_NumJoysticks()
print(f'{n} joystick(s)')
for i in range(n):
    g = bytes(sdl.SDL_JoystickGetDeviceGUID(i).data).hex()
    j = sdl.SDL_JoystickOpen(i)
    print(f'  [{i}] {sdl.SDL_JoystickNameForIndex(i).decode()}  vid:pid={sdl.SDL_JoystickGetDeviceVendor(i):04x}:'
          f'{sdl.SDL_JoystickGetDeviceProduct(i):04x}  guid={g}  path={(sdl.SDL_JoystickPathForIndex(i) or b"").decode()}  '
          f'buttons={sdl.SDL_JoystickNumButtons(j)} axes={sdl.SDL_JoystickNumAxes(j)} hats={sdl.SDL_JoystickNumHats(j)}')
sdl.SDL_Quit()
