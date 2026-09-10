#include <stdio.h>
// M0_E_MEMORY â€” read/write state (array)
// store 10,20,30 sum=60 -> print "60\n" via arithmetic
int main() {
    int mem[3];
    mem[0] = 10;
    mem[1] = 20;
    mem[2] = 30;
    int s = mem[0] + mem[1] + mem[2]; // 60
    int tens = 0;
    int tmp = s;
    while (tmp >= 10) { tmp -= 10; tens++; }
    putchar(tens + 48);
    putchar(tmp + 48);
    putchar('\n');
    return 0;
}

