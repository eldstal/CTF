#!/usr/bin/env python3

import argparse

import frontend.debug
import middleend.basic
import backend.demo


def main():
    print("Let's do this")

    f = frontend.debug.FrontEnd()
    m = middleend.basic.MiddleEnd(f)
    b = backend.demo.BackEnd(m)


if __name__ == "__main__":
    main()
