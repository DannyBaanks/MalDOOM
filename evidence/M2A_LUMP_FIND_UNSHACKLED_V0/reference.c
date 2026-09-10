#include <stdio.h>
#include <string.h>
/* M2a reference: stdin = 144 ASCII hex chars = 8 query bytes + 4x16 record bytes.
   Prints MATCH idx/filepos/size or NOMATCH. Record: filepos 0-3 LE, size 4-7 LE, name 8-15. */
static int hexv(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
int main(void) {
    unsigned char b[72];
    for (int i = 0; i < 72; i++) {
        int hi = getchar(), lo = getchar();
        int a = hexv(hi), c = hexv(lo);
        if (a < 0 || c < 0) return 1;
        b[i] = (unsigned char)(a * 16 + c);
    }
    for (int r = 0; r < 4; r++) {
        if (memcmp(b, b + 16 + 16 * r, 8) == 0) {
            long fp = (long)b[8 + 16*r] | ((long)b[9 + 16*r] << 8)
                    | ((long)b[10 + 16*r] << 16) | ((long)b[11 + 16*r] << 24);
            long sz = (long)b[12 + 16*r] | ((long)b[13 + 16*r] << 8)
                    | ((long)b[14 + 16*r] << 16) | ((long)b[15 + 16*r] << 24);
            printf("MATCH\n%d\n%ld\n%ld\n", r, fp, sz);
            return 0;
        }
    }
    printf("NOMATCH\n");
    return 0;
}
