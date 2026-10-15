/* M2-full reference oracle (host side).
 *
 * NOT the claimant: it computes the expected S_0 text from the same WAD bytes
 * so the verifier can compare byte-for-byte with the VM output. The VM
 * artifact itself receives only the content-blind hex framing of one THINGS
 * lump on stdin and derives everything it prints.
 *
 *   ./reference <doom1.wad> E1M1
 *   -> S0V1 x=1056 y=-3616 angle=90 things=138 p1=1
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *wad;
static long wad_len;

static long rd32(long off) {
    return (long)wad[off] | ((long)wad[off + 1] << 8)
         | ((long)wad[off + 2] << 16) | ((long)wad[off + 3] << 24);
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: reference wad map\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("wad"); return 2; }
    fseek(f, 0, SEEK_END); wad_len = ftell(f); fseek(f, 0, SEEK_SET);
    wad = malloc(wad_len);
    if (fread(wad, 1, wad_len, f) != (size_t)wad_len) { perror("read"); return 2; }
    fclose(f);
    if (memcmp(wad, "IWAD", 4) != 0) { fprintf(stderr, "not an IWAD\n"); return 2; }
    long numlumps = rd32(4), diroff = rd32(8);
    const char *map = argv[2];

    long e1m1_idx = -1, things_pos = -1, things_size = -1;
    for (long i = 0; i < numlumps; i++) {
        long off = diroff + i * 16;
        char name[9]; memcpy(name, wad + off + 8, 8); name[8] = 0;
        if (e1m1_idx < 0 && strcmp(name, map) == 0) { e1m1_idx = i; continue; }
        if (e1m1_idx >= 0) {
            if (strcmp(name, "THINGS") == 0) {
                things_pos = rd32(off); things_size = rd32(off + 4);
                break;
            }
            /* next map lump reached without a THINGS in between */
            if (name[0] == 'E' && name[1] == '1' && name[2] == 'M') break;
        }
    }
    if (things_pos < 0) { fprintf(stderr, "THINGS not found after %s\n", map); return 1; }

    long records = things_size / 10;
    int p1 = 0; long px = 0, py = 0, pang = 0;
    for (long i = 0; i < records; i++) {
        long off = things_pos + i * 10;
        long typ = (long)wad[off + 6] | ((long)wad[off + 7] << 8);
        if (typ == 1) {
            short x = (short)((long)wad[off] | ((long)wad[off + 1] << 8));
            short y = (short)((long)wad[off + 2] | ((long)wad[off + 3] << 8));
            unsigned short ang = (unsigned short)((long)wad[off + 4] | ((long)wad[off + 5] << 8));
            px = x; py = y; pang = ang; p1++;
        }
    }
    printf("S0V1 x=%ld y=%ld angle=%ld things=%ld p1=%d\n", px, py, pang, records, p1);
    free(wad);
    return 0;
}
