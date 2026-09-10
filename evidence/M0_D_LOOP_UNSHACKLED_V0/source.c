#include <stdio.h>
// M0_D_LOOP â€” real loop inside VM (5 iterations)
int main() {
    int i = 0;
    while (i < 5) {
        putchar('*');
        i = i + 1;
    }
    putchar('\n');
    return 0;
}

