#include <stdio.h>
// M0_B_ARITH â€” arithmetic inside the VM (40 + 2 = 42)
// Host must not compute 42.
int main() {
    int a = 40;
    int b = 2;
    int c = a + b; // EIR add
    // print "42\n" without hardcoding '4'/'2' â€” compute digits
    // c = 42 -> '4' = 52, '2' = 50 via division by 10
    int tens = 0;
    int tmp = c;
    while (tmp >= 10) { tmp = tmp - 10; tens = tens + 1; }
    int ones = tmp;
    putchar(tens + 48);
    putchar(ones + 48);
    putchar('\n');
    return 0;
}

