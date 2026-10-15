import re, sys, os
src = os.environ.get("SRC", "unsh_pin.c"); dst = os.environ.get("DST", "unsh_pinned.c")
s = open(src).read()

# 0) includes
add_inc = '#include <stdlib.h>\n#include <sys/time.h>\n'
if '#include <stdlib.h>' not in s:
    s = s.replace('#include <malloc.h>', '#include <malloc.h>\n' + add_inc, 1)

# 1) bloque de sorteo -> configurable por env, con Defaults = comportamiento original
pat_cfg = re.compile(
 r"srand\(time\(NULL\)\);\s*\n\s*uintmax_t rotwidth = 10 \+ rand\(\)%6;\s*\n"
 r"\s*uintmax_t growth_slack = rand\(\) % 6;\s*\n\s*uintmax_t growth_step = 4 \+ rand\(\) % 9;\s*\n"
 r"\s*uintmax_t growth_prob;\s*\n\s*do \{\s*\n\s*growth_prob = rand\(\);\s*\n"
 r"\s*\} while \(growth_prob < RAND_MAX/5 \|\| growth_prob/4 > RAND_MAX/5\);\s*\n"
 r"\s*int det_growth = rand\(\)%2;")
rep_cfg = r"""unsigned int unsh_seed = (unsigned int)time(NULL);
	{ const char* _e = getenv("UNSH_SEED"); if (_e) unsh_seed = (unsigned int)strtoul(_e,0,10); }
	srand(unsh_seed);
	#define UNSH_ENV(NAME, DFLT) ({ unsigned long _v = (DFLT); const char* _e = getenv(NAME); if (_e) _v = strtoul(_e,0,10); _v; })
	uintmax_t rotwidth = UNSH_ENV("UNSH_ROTWIDTH", 10 + rand()%6);
	uintmax_t growth_slack = UNSH_ENV("UNSH_GROWTH_SLACK", rand()%6);
	uintmax_t growth_step = UNSH_ENV("UNSH_GROWTH_STEP", 4 + rand()%9);
	uintmax_t growth_prob = UNSH_ENV("UNSH_GROWTH_PROB", (unsigned long)(RAND_MAX/2));
	int det_growth = (int)UNSH_ENV("UNSH_DET_GROWTH", rand()%2);
	uintmax_t rotwidth0 = rotwidth;"""
s, n = pat_cfg.subn(rep_cfg, s); assert n == 1, f"cfg block: {n}"

# 2) contador de pasos + reloj (step pasa a uintmax_t)
s, n = re.subn(r"\tint step = 1;\n",
 r"\tuintmax_t step = 1;\n\tstruct timeval unsh_t0, unsh_t1;\n\tgettimeofday(&unsh_t0, NULL);\n", s)
assert n == 1, f"step decl: {n}"

# 3) reporte en hlt
s, n = re.subn(r"\t\t\tcase 81: // hlt\n\t\t\t\treturn 0;",
 r'\t\t\tcase 81: { // hlt\n'
 r'\t\t\t\tgettimeofday(&unsh_t1, NULL);\n'
 r'\t\t\t\tdouble el = (unsh_t1.tv_sec-unsh_t0.tv_sec) + (unsh_t1.tv_usec-unsh_t0.tv_usec)/1e6;\n'
 r'\t\t\t\tif (el <= 0) el = 1e-9;\n'
 r'\t\t\t\tfprintf(stderr,"UNSH_PIN STEPS %llu WALL %.3fs SPS %.0f cfg{seed=%u rotwidth0=%llu slack=%llu gstep=%llu det=%d prob=%llu} final{rotwidth=%llu max_wordwidth=%llu}\\n",\n'
 r'\t\t\t\t\t(unsigned long long)step, el, (double)step/el, unsh_seed,\n'
 r'\t\t\t\t\t(unsigned long long)rotwidth0, (unsigned long long)growth_slack, (unsigned long long)growth_step,\n'
 r'\t\t\t\t\tdet_growth, (unsigned long long)growth_prob,\n'
 r'\t\t\t\t\t(unsigned long long)rotwidth, (unsigned long long)max_wordwidth);\n'
 r'\t\t\t\treturn 0;\n\t\t\t}', s)
assert n == 1, f"hlt: {n}"

# 4) fix de formato en el camino de error (step ahora uintmax_t)
s, n = s.replace('invalid instruction in step %d', 'invalid instruction in step %llu').__iter__().__length_hint__() if False else re.subn(
 r'fprintf\(stderr,"error: invalid instruction in step %d\\n",step\);',
 r'fprintf(stderr,"error: invalid instruction in step %llu\\n",(unsigned long long)step);', s)
print(f"error-path fix: {n}", file=sys.stderr)
open(dst,"w").write(s)
print(f"OK -> {dst} ({len(s)} bytes)")
