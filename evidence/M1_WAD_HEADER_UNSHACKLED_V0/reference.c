#include <stdio.h>
/* M1 reference: parse 12-byte WAD header from stdin, print ident/numlumps/infotableofs. */
int main(void) {
    unsigned char h[12];
    if (fread(h, 1, 12, stdin) != 12) return 1;
    printf("%c%c%c%c\n%d\n%d\n", h[0], h[1], h[2], h[3],
        (int)(h[4] | (h[5] << 8) | (h[6] << 16) | (h[7] << 24)),
        (int)(h[8] | (h[9] << 8) | (h[10] << 16) | (h[11] << 24)));
    return 0;
}
