#!/usr/bin/env py
import sys
sys.path.insert(0, r"C:\Development\ISyCo Git\Walbolge")
from walbolge.trace import trace_program

XLAT1 = "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"

def enc(inst: str, pos: int) -> str:
    return chr((XLAT1.index(inst) - pos) % 94 + 33)

# Test: program that increments tape[0] then halts
# p rotates tape[0] and writes back
# v halts
enc_p = enc('p', 0)
enc_v = enc('v', 1)
prog = enc_p + enc_v
print('Program:', prog)

# Capture tape with on_step
captured_tape = None
def on_step(ev, tape):
    global captured_tape
    # Make a copy of the tape
    captured_tape = tape.copy()

trace = trace_program(prog, max_steps=10, classic=True, on_step=on_step)
print('steps:', trace.steps)
print('halted:', trace.halted)
print('halt_reason:', trace.halt_reason)

if captured_tape is not None:
    print('captured tape[0]:', captured_tape[0] if len(captured_tape) > 0 else 'empty')
    print('captured tape len:', len(captured_tape))
else:
    print('No tape captured')

# Also check the last event
if trace.events:
    last = trace.events[-1]
    print('final a_after:', last.a_after)
    print('final c:', last.c)
    print('final d:', last.d)