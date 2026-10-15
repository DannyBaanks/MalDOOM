// b19var - scratch fork of bolge19 (fixed-19 engine) with runtime semantic switches.
// Goal: isolate WHY a LMFAO (Unshackled) .mu image breaks on fast20-style engines.
// NOTHING here is repo evidence; scratch only.
const std = @import("std");

extern "c" fn fopen(filename: [*:0]const u8, modes: [*:0]const u8) ?*anyopaque;
extern "c" fn fclose(stream: ?*anyopaque) c_int;
extern "c" fn fseek(stream: ?*anyopaque, offset: c_long, whence: c_int) c_int;
extern "c" fn ftell(stream: ?*anyopaque) c_long;
extern "c" fn rewind(stream: ?*anyopaque) void;
extern "c" fn fread(ptr: [*]u8, size: usize, n: usize, stream: ?*anyopaque) usize;
extern "c" fn read(fd: c_int, buf: [*]u8, count: usize) isize;
extern "c" fn write(fd: c_int, buf: [*]const u8, count: usize) isize;

const timeval = extern struct { sec: isize, usec: i64 };
extern "c" fn gettimeofday(tv: ?*timeval, tz: ?*anyopaque) c_int;
const SEEK_SET: c_int = 0;
const SEEK_END: c_int = 2;

const END: u64 = 1162261467; // 3^19
const THIRD: u64 = END / 3; // 3^18
const NL_SENT: u32 = @truncate(END - 2); // ...2221 == -2 (canonical newline)
const EOF_SENT: u32 = @truncate(END - 1); // ...2222 == -1 (canonical EOF)

const XLAT_CONCAT =
    "SOMEBODY MAKE ME FEEL ALIVE" ++
    "[hj9>,5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@" ++
    "AND SHATTER ME";

const CRAZY_TBL = [3][3]u8{ .{ 1, 0, 0 }, .{ 1, 0, 2 }, .{ 2, 2, 1 } };
const CRZ2 = [144]u8{
    4, 3, 3, 1, 0, 0, 1, 0, 0, 9, 9, 9, 9, 9, 9, 9,
    4, 3, 5, 1, 0, 2, 1, 0, 2, 9, 9, 9, 9, 9, 9, 9,
    5, 5, 4, 2, 2, 1, 2, 2, 1, 9, 9, 9, 9, 9, 9, 9,
    4, 3, 3, 1, 0, 0, 7, 6, 6, 9, 9, 9, 9, 9, 9, 9,
    4, 3, 5, 1, 0, 2, 7, 6, 8, 9, 9, 9, 9, 9, 9, 9,
    5, 5, 4, 2, 2, 1, 8, 8, 7, 9, 9, 9, 9, 9, 9, 9,
    7, 6, 6, 7, 6, 6, 4, 3, 3, 9, 9, 9, 9, 9, 9, 9,
    7, 6, 8, 7, 6, 8, 4, 3, 5, 9, 9, 9, 9, 9, 9, 9,
    8, 8, 7, 8, 8, 7, 5, 5, 4, 9, 9, 9, 9, 9, 9, 9,
};

inline fn mcrz(a_in: u32, d_in: u32) u32 {
    var r: u32 = 0;
    var k: u32 = 1;
    var a: u32 = a_in;
    var d: u32 = d_in;
    comptime var pass = 0;
    inline while (pass < 9) : (pass += 1) {
        r +%= k *% CRZ2[(a % 9) + 16 * (d % 9)];
        a /= 9;
        d /= 9;
        k *%= 9;
    }
    r +%= k *% @as(u32, CRAZY_TBL[d % 3][a % 3]);
    return r;
}

// rot over an arbitrary window of `w` trits (w=18 reproduces fast20/bolge19 exactly;
// w=19 rotates the whole 3^19 word; w<19 mimics a canonical epochal window of that size).
inline fn mrot_w(x: u32, w: u32) u32 {
    var t: u64 = 1;
    var i: u32 = 0;
    while (i < w) : (i += 1) t *= 3;
    const tt: u32 = @intCast(t); // 3^w
    const b = x % tt;
    const m = b % 3;
    const q = b / 3;
    return q +% m *% (tt / 3) +% (x -% b);
}

const PAGE: usize = 65536;

var image: []u32 = &[_]u32{};
var img_len: usize = 0;
var chain_zone: []u32 = &[_]u32{};
var zone_start: usize = 0;
var pat: [6]u32 = .{0} ** 6;
var overlay: std.AutoHashMapUnmanaged(u32, u32) = .{};
var alloc: std.mem.Allocator = undefined;

fn initAfterLoad() void {
    zone_start = ((img_len + PAGE - 1) / PAGE) * PAGE;
    const zlen = zone_start - img_len;
    chain_zone = alloc.alloc(u32, zlen) catch @panic("oom");
    var p2: u32 = if (img_len >= 2) image[img_len - 2] else 0;
    var p1: u32 = if (img_len >= 1) image[img_len - 1] else 0;
    var i: usize = 0;
    while (i < zlen) : (i += 1) {
        const nxt = mcrz(p1, p2);
        chain_zone[i] = nxt;
        p2 = p1;
        p1 = nxt;
    }
    var k: usize = 0;
    while (k < 6) : (k += 1) {
        const nxt = mcrz(p1, p2);
        pat[k] = nxt;
        p2 = p1;
        p1 = nxt;
    }
}

fn beyondVal(i: usize) u32 {
    if (i < zone_start) return chain_zone[i - img_len];
    const pbase = i & ~(PAGE - 1);
    const phase: usize = @intCast(@mod(@as(u64, pbase) % THIRD + (i - pbase), 6));
    return pat[phase];
}

fn memGet(i: usize) u32 {
    if (i < img_len) return image[i];
    if (overlay.get(@intCast(i))) |v| return v;
    return beyondVal(i);
}

fn memSet(i: usize, v: u32) void {
    if (i < img_len) {
        image[i] = v;
    } else {
        overlay.put(alloc, @intCast(i), v) catch @panic("oom");
    }
}

fn tickMs() u64 {
    var tv: timeval = undefined;
    _ = gettimeofday(&tv, null);
    return @as(u64, @intCast(tv.sec)) * 1000 + @as(u64, @intCast(tv.usec)) / 1000;
}

fn wout(s: []const u8) void {
    _ = write(1, s.ptr, s.len);
}

extern "c" fn getenv(name: [*:0]const u8) ?[*:0]const u8;

fn envi(name: []const u8, dflt: i64) i64 {
    const p = getenv(alloc.dupeZ(u8, name) catch return dflt) orelse return dflt;
    return std.fmt.parseInt(i64, std.mem.span(p), 10) catch dflt;
}

pub fn main(init: std.process.Init.Minimal) !void {
    alloc = std.heap.page_allocator;

    const rotw: u32 = @intCast(@max(1, @min(19, envi("B19_ROTW", 18))));
    const io_canon = envi("B19_IO_CANON", 0) != 0;
    const trim = envi("B19_TRIM", 0) != 0;
    const zero_offs = envi("B19_OFFS_ZERO", 0) != 0;
    const check_print = envi("B19_CHECK", 0) != 0;
    const trace_n: u64 = @intCast(envi("B19_TRACE", 0));
    const max_steps: u64 = @intCast(envi("B19_MAXSTEPS", 200_000_000));

    var it = init.args.iterate();
    _ = it.next();
    var path_u8: ?[]const u8 = null;
    while (it.next()) |arg| {
        if (!std.mem.startsWith(u8, arg, "--")) path_u8 = arg;
    }
    if (path_u8 == null) {
        std.debug.print("uso: b19var <imagen.mu>\n", .{});
        return;
    }

    const c_path = try alloc.dupeZ(u8, path_u8.?);
    defer alloc.free(c_path);
    const f = fopen(c_path.ptr, "rb");
    if (f == null) {
        std.debug.print("b19var: no pude abrir {s}\n", .{path_u8.?});
        return;
    }
    defer _ = fclose(f);
    _ = fseek(f, 0, SEEK_END);
    const fsize = ftell(f);
    rewind(f);
    if (fsize <= 0) {
        std.debug.print("b19var: tamano invalido\n", .{});
        return;
    }
    const raw_len: usize = @intCast(fsize);
    const raw = alloc.alloc(u8, raw_len) catch @panic("oom");
    defer alloc.free(raw);
    if (fread(raw.ptr, 1, raw_len, f) != raw_len) {
        std.debug.print("b19var: lectura corta\n", .{});
        return;
    }

    image = alloc.alloc(u32, raw_len) catch @panic("oom");
    if (trim) {
        // canonical Unshackled loader: skip ' \t\r\n', require 33<=v<127 and
        // (v+pos)%94 in the opcode set, pos++ mod 564 per accepted cell.
        const ALLOW = [8]u64{ 4, 5, 23, 39, 40, 62, 68, 81 };
        var pos: i64 = 0;
        img_len = 0;
        for (raw, 0..) |v, i| {
            if (v == ' ' or v == '\t' or v == '\r' or v == '\n') continue;
            const instr = @mod(@as(i64, v) + @as(i64, pos), 94);
            var ok = false;
            for (ALLOW) |a| {
                if (a == instr) ok = true;
            }
            if (!(v >= 33 and v < 127 and ok)) {
                std.debug.print("b19var: invalid character byte={d} v={d} instr={d}\n", .{ i, v, instr });
                return;
            }
            image[img_len] = v;
            img_len += 1;
            pos += 1;
            pos = @mod(pos, 564);
        }
    } else {
        img_len = raw_len;
        for (raw, 0..) |byte, i| image[i] = byte;
    }
    initAfterLoad();

    var a: u32 = 0;
    var c: u64 = 0;
    var d: u64 = 0;
    var steps: u64 = 0;
    var outs: u64 = 0;
    var ins: u64 = 0;
    var abort_reason: []const u8 = "halt";

    var offs: [3]i64 = .{ 0, 0, 0 };
    if (!zero_offs) {
        const a1_off: i64 = 94 - @mod(@as(i64, @intCast((END - 1) / 6)) - 29524, 94);
        const a2_off: i64 = 94 - @mod(@as(i64, @intCast((END - 1) / 3)) - 59048, 94);
        offs[1] = @mod(a1_off - @as(i64, @intCast(THIRD)), 94) + 94;
        offs[2] = a2_off - @as(i64, @intCast(@mod(2 * THIRD, 94))) + 94;
    }

    const t0 = tickMs();
    var in_buf: [1]u8 = undefined;

    while (true) {
        if (max_steps != 0 and steps >= max_steps) {
            abort_reason = "maxsteps";
            break;
        }
        const cu: u32 = @truncate(c);
        const cv = memGet(cu);
        if (check_print and (cv < 33 or cv > 126)) {
            std.debug.print("b19var: INVALID INSTRUCTION step={d} c={d} val={d}\n", .{ steps, cu, cv });
            abort_reason = "invalid_instr";
            break;
        }
        const region = cu / @as(u32, @intCast(THIRD));
        const off_i: i64 = if (region < 3) offs[region] else 0;
        const idx: usize = @intCast(@mod(@as(i64, cu) + @as(i64, cv) + off_i, 94));
        if (steps < trace_n) {
            std.debug.print("TR step={d} c={d} val={d} reg={d} off={d} op={d} a={d} d={d}\n", .{ steps, cu, cv, region, off_i, idx, a, d });
        }
        switch (idx) {
            4 => c = memGet(@truncate(d)),
            5 => {
                outs += 1;
                if (io_canon) {
                    if (a == NL_SENT) {
                        wout("\n");
                    } else if (a == EOF_SENT) {
                        std.debug.print("b19var: print of EOF sentinel (canonical would abort)\n", .{});
                        abort_reason = "print_eof";
                        break;
                    } else if (a < 0x80) {
                        const ob = [_]u8{@truncate(a)};
                        wout(&ob);
                    } else if (a < 0x800) {
                        const ob = [_]u8{ @truncate(0xC0 | (a >> 6)), @truncate(0x80 | (a & 0x3F)) };
                        wout(&ob);
                    } else {
                        const ob = [_]u8{ @truncate(0xE0 | (a >> 12)), @truncate(0x80 | ((a >> 6) & 0x3F)), @truncate(0x80 | (a & 0x3F)) };
                        wout(&ob);
                    }
                } else {
                    const ob = [_]u8{@truncate(a)};
                    wout(&ob);
                }
            },
            23 => {
                const n = read(0, &in_buf, 1);
                ins += 1;
                if (io_canon) {
                    a = if (n <= 0) EOF_SENT else if (in_buf[0] == '\n') NL_SENT else in_buf[0];
                } else {
                    a = if (n <= 0) EOF_SENT else in_buf[0];
                }
            },
            39 => {
                const du: u32 = @truncate(d);
                const r = mrot_w(memGet(du), rotw);
                memSet(du, r);
                a = r;
            },
            40 => d = memGet(@truncate(d)),
            62 => {
                const du: u32 = @truncate(d);
                const r = mcrz(a, memGet(du));
                memSet(du, r);
                a = r;
            },
            81 => {
                abort_reason = "halt";
                break;
            },
            else => {},
        }
        const cur: u32 = @truncate(c);
        const curv = memGet(cur);
        if (curv < XLAT_CONCAT.len) memSet(cur, XLAT_CONCAT[curv]);
        c = (c + 1) % END;
        d = (d + 1) % END;
        steps += 1;
    }
    std.debug.print("B19V rotw={d} io={s} trim={d} offs={s} check={d} => {s} steps={d} outs={d} ins={d} c={d} d={d} a={d} overlay={d} elapsed={d}ms\n", .{
        rotw,       if (io_canon) "canon" else "raw", @intFromBool(trim),
        if (zero_offs) "zero" else "fast20", @intFromBool(check_print),
        abort_reason, steps,    outs,       ins,      c,                d,      a,
        overlay.count(),        tickMs() - t0,
    });
}
