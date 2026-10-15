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

trace = trace_program(enc_p + enc_v, max_steps=10, classic=True)
print('Encoded program:', enc_p + enc_v)
print('  steps:', trace.steps)
print('  halted:', trace.halted)
print('  halt_reason:', trace.halt_reason)
if trace.events:
    for i, e in enumerate(trace.events):
        print('  event {}: a_before={}, a_after={}, c={}, d={}, inst={}'.format(i, e.a_before, e.a_after, e.c, e.d, e.instruction))

# Test tape state
final_tape = []
def on_step(ev, tape):
    print('  on_step: tape[0]=', tape[0] if len(tape) > 0 else 'empty')

trace2 = trace_program(enc_p + enc_v, max_steps=10, classic=True, on_step=on_step)
print('  final tape[0]:', final_tape[0] if len(final_tape) > 0 else 'empty')