#include <stdio.h>
// M0_KILLER â€” runtime-unknown input test
// Host only delivers n. VM must compute deterministic arithmetic/control result.
// Reads single digit '0'..'4', computes n*2 + 1, outputs single digit (1,3,5,7,9)
// Same .mu must work for any n without recompilation or host help.
// If generator hardcodes answer per n, FAIL.
int main() {
    int c = getchar();
    if (c == 10 || c == 13) c = getchar();
    if (c < 48 || c > 57) { putchar('?'); putchar('\n'); return 1; }
    int n = c - 48;
    // clamp to 0..4 so output is single digit (n*2+1 = 1,3,5,7,9)
    // branch and arithmetic + loop (via multiplication loop)
    int doubled = 0;
    int i = 0;
    while (i < n) { doubled = doubled + 2; i = i + 1; }
    int result = doubled + 1; // 1..9
    // loop for multiply proves control flow inside VM
    if (result < 0 || result > 9) { putchar('X'); putchar('\n'); return 0; }
    putchar(result + 48);
    putchar('\n');
    return 0;
}

