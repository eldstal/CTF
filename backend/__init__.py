import backend.demo
import backend.auto

BACKENDS = {
              "demo" : backend.demo.BackEnd,
              "auto" : backend.auto.SelectBackend,
           }
