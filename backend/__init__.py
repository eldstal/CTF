# Special backends
import backend.auto
import backend.demo

# Specific implementations for scoreboard managers
import backend.rctf  # Introduced for diceCTF 2021
import backend.ctfd  # This is a pretty popular system

BACKENDS = {
              "demo" : backend.demo.BackEnd,
              "ctfd" : backend.ctfd.BackEnd,
              "rctf" : backend.rctf.BackEnd,

              # This is a function and not a class. Call it like the standard BackEnd constructor to autodetect
              "auto" : backend.auto.SelectBackend,
           }
