# HOST_AUDIT — V1 (dumb pipe, to be verified)

Allowed in host/v1_anchor_pipe.py:
- Popen(gost/oracle, program_v1.mal)
- read stdout, detect framing "INPUT\n", "ANCHOR\n", "STATE:", "REJECT\n"
- write stdin one byte
- store opaque anchor bytes
- SHA256, PID, timing

Forbidden (static grep must find 0 hits):
- anchor_decode, anchor_encode, epoch, acc, rng, reference_step, split("-"), int(anchor), checksum, state

If host needs anchor length, use terminator \n, not parsing.
