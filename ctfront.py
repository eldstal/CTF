#!/usr/bin/env python3

import argparse

import frontend.debug
import middleend.basic
import backend.demo


def main():
    print("Let's do this")

    conf = {}

    f = frontend.debug.FrontEnd(conf)
    m = middleend.basic.MiddleEnd(conf, [f])
    b = backend.demo.BackEnd(conf, m)

    b.start()


if __name__ == "__main__":
    main()
