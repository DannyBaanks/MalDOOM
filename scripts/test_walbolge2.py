#!/usr/bin/env py
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")
from walbolge.trace import trace_program

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"

def enc(inst: str, pos: int) -> str:
    return chr((XLAT1.index(inst) - pos) % 94 + 33)

# Test p at position 0, v at position 1
enc_p = enc('p', 0)
enc_v = enc('v', 1)
print('Encoded pv:', enc_p + enc_v)

# Capture tape with on_step
final_tape = []
def on_step(ev, tape):
    # Make a copy
    pass

# Use trace_program with max_events to capture all events
trace = trace_program(enc_p + enc_v, max_steps=10, classic=True, max_events=100)
print('steps:', trace.steps)
print('halted:', trace.halted)
print('halt_reason:', trace.halt_reason)

# Check tape via events
if trace.events:
    last = trace.events[-1]
    print('final a_after:', last.a_after)
    print('final c:', last.c)
    print('final d:', last.d)

# The tape is not directly exposed in trace result, but we can use the on_step callback
# Let's see if we can get tape from the trace
print('trace keys:', dir(trace))