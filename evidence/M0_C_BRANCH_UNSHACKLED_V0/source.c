#include <stdio.h>
// M0_C_BRANCH â€” conditional inside VM
// fixed input 1 -> should take else branch -> "NONZERO\n"
// branch is computed via setcc/jcc in EIR
int main() {
    int x = 1;
    if (x == 0) {
        putchar('Z');
        putchar('E');
        putchar('R');
        putchar('O');
    } else {
        putchar('N');
        putchar('O');
        putchar('N');
        putchar('Z');
        putchar('E');
        putchar('R');
        putchar('O');
    }
    putchar('\n');
    return 0;
}

