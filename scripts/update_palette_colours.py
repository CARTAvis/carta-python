#!/bin/env python3

import sys
import re

if len(sys.argv) < 2:
    sys.exit("Usage: update_palette_colours.py /path/to/blueprint/colors.ts")

blueprint_source = sys.argv[1]

with open(blueprint_source) as f:
    data = f.read()

colours = {k:v for k, v in re.findall(' *([A-Z_]+\d?): "(#[A-F0-9]+)"', data)}

def print_palette(number):
    for k, v in colours.items():
        if k in {"BLACK", "WHITE"}:
            print(f'    "{k}": "{v.lower()}",')
        elif k.endswith(str(number)):
            print(f'    "{k[:-1]}": "{v.lower()}",')

print("LIGHT_THEME = {")
print_palette(2)
print("}")
print("")
print("DARK_THEME = {")
print_palette(4)
print("}")
