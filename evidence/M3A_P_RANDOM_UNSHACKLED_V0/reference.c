#include <stdio.h>
/* M3a reference: links Doom's ACTUAL P_Random (m_random.c) and runs the same
   3-tick x 8-draw framing as the VM. stdin: leveltime(4B LE) + idx(1B) hex-framed. */
int P_Random(void);
extern int prndindex;
int leveltime = 0;

static int hexv(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
int main(void) {
    unsigned char b[5];
    for (int i = 0; i < 5; i++) {
        int a = hexv(getchar()), c = hexv(getchar());
        if (a < 0 || c < 0) return 1;
        b[i] = (unsigned char)(a * 16 + c);
    }
    leveltime = b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24);
    prndindex = b[4];
    for (int t = 0; t < 3; t++) {
        for (int k = 0; k < 8; k++)
            printf("%d\n", P_Random());
        leveltime++;
    }
    printf("%d\n%d\n", leveltime, prndindex);
    return 0;
}
