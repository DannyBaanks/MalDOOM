#include "doomgeneric/doomgeneric.h"
#include <stdio.h>
#include <string.h>
#include <sys/time.h>

// DG_ScreenBuffer is defined in doomgeneric.c
int DG_nFrames = 0;
int DG_ScreenWidth = 640;
int DG_ScreenHeight = 400;

// dummy sound stubs — we don't need audio for headless test
void I_InitSound(int a){ (void)a; }
void I_ShutdownSound(void){}
void I_SetMusicVolume(int a){ (void)a; }
void I_ShutdownMusic(void){}
void I_InitMusic(void){}
int I_MusicIsPlaying(void){ return 0; }
int snd_musicdevice = 0;
void I_UpdateSound(void){}
void I_UpdateSoundParams(int a,int b,int c){ (void)a;(void)b;(void)c; }
int I_GetSfxLumpNum(void* a){ (void)a; return 0; }
void* I_RegisterSong(void* a, int b){ (void)a;(void)b; return 0; }
void I_PlaySong(void* a,int b){ (void)a;(void)b; }
void I_StopSong(void* a){ (void)a; }
void I_UnRegisterSong(void* a){ (void)a; }
void I_PauseSong(void* a){ (void)a; }
void I_ResumeSong(void* a){ (void)a; }
int I_SoundIsPlaying(int a){ (void)a; return 0; }
void I_StopSound(int a){ (void)a; }
int I_StartSound(int a,int b,int c,int d){ (void)a;(void)b;(void)c;(void)d; return 0; }
void I_PrecacheSounds(void* a,int b){ (void)a;(void)b; }
void I_BindSoundVariables(void){}

void DG_Init() {
    DG_ScreenBuffer = (pixel_t*)malloc(DG_ScreenWidth*DG_ScreenHeight*sizeof(pixel_t));
    memset(DG_ScreenBuffer, 0, DG_ScreenWidth*DG_ScreenHeight*sizeof(pixel_t));
    printf("[headless] DG_Init %dx%d\n", DG_ScreenWidth, DG_ScreenHeight);
}
void DG_DrawFrame() {
    DG_nFrames++;
    if (DG_nFrames % 35 == 0) {
        // hash simple
        unsigned long h = 0;
        for (int i=0;i<100;i++) h = h*31 + DG_ScreenBuffer[i];
        printf("[headless] frame %d hash %08lx\n", DG_nFrames, h);
    }
}
void DG_SleepMs(uint32_t ms) {
    // no sleep for test
}
uint32_t DG_GetTicksMs() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (tv.tv_sec*1000 + tv.tv_usec/1000);
}
int DG_GetKey(int* pressed, unsigned char* key) {
    return 0;
}
void DG_SetWindowTitle(const char* title) {
    printf("[headless] title: %s\n", title);
}
int main(int argc, char** argv) {
    printf("doomgeneric headless test\n");
    doomgeneric_Create(argc, argv);
    for (int i=0;i<50;i++) {
        doomgeneric_Tick();
        if (i==5) printf("TICK 5 OK — Doom corre de verdad\n");
    }
    printf("50 ticks done, frames %d\n", DG_nFrames);
    // dump first pixels
    printf("first 10 pixels: ");
    for (int i=0;i<10;i++) printf("%08x ", DG_ScreenBuffer[i]);
    printf("\n");
    return 0;
}
