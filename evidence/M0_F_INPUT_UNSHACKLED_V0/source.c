#include <stdio.h>
// M0_F_INPUT â€” input modifies result (host only delivers byte)
// read single digit char '0'..'9', echo incremented digit (wrap 9->0)
// tests getc/putc through Unshackled VM
int main() {
    int c = getchar(); // HeLL getc: Unicode codepoint mod 256, ASCII only
    if (c < 0) return 1;
    // strip newline if host sends "5\n", we want '5'
    if (c == 10 || c == 13) c = getchar();
    if (c >= 48 && c <= 57) {
        int d = c - 48;
        d = d + 1;
        if (d >= 10) d = 0;
        putchar(d + 48);
        putchar('\n');
    } else {
        putchar('?');
        putchar('\n');
    }
    return 0;
}

