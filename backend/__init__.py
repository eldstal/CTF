# Special backends
import backend.auto
import backend.demo

# Specific implementations for scoreboard managers
import backend.rctf          # Introduced for diceCTF 2021
import backend.ractf         # Used by Really Awesome CTF and RaRCTF
import backend.ctfd          # This is a pretty popular system
import backend.hxp           # Custom but predictable. We love hxp CTF!
import backend.rtbctf        # RootTheBox CTF. Doesn't give us solves, sadly.
import backend.angstrom      # ÅngströmCTF seems to have a stable API
import backend.midnightsun   # Based on MidnightSun 2021 qualifiers

# One-offs and custom jobs
import backend.zer0pts   # Modeled after zer0pts CTF 2021

BACKENDS = {
              "demo"     : backend.demo.BackEnd,
              "ctfd"     : backend.ctfd.BackEnd,
              "rctf"     : backend.rctf.BackEnd,
              "rtbctf"   : backend.rtbctf.BackEnd,
              "ractf"    : backend.ractf.BackEnd,

              # Potential one-offs. These are down here because they are super
              # unlikely to be relevant during autodetection
              "angstrom"     : backend.angstrom.BackEnd,
              "hxp"          : backend.hxp.BackEnd,
              "midnightsun"  : backend.midnightsun.BackEnd,
              "zer0pts"      : backend.zer0pts.BackEnd,

              # This is a function and not a class. Call it like the standard BackEnd constructor to autodetect
              "auto" : backend.auto.SelectBackend,
           }
