# Special backends
import backend.auto
import backend.demo

# Specific implementations for scoreboard managers
import backend.rctf    # Introduced for diceCTF 2021
import backend.ctfd    # This is a pretty popular system
import backend.hxp     # Custom but predictable. We love hxp CTF!
import backend.rtbctf  # RootTheBox CTF. Doesn't give us solves, sadly.

BACKENDS = {
              "demo"   : backend.demo.BackEnd,
              "ctfd"   : backend.ctfd.BackEnd,
              "rctf"   : backend.rctf.BackEnd,
              "rtbctf" : backend.rtbctf.BackEnd,
              "hxp"    : backend.hxp.BackEnd,

              # This is a function and not a class. Call it like the standard BackEnd constructor to autodetect
              "auto" : backend.auto.SelectBackend,
           }
