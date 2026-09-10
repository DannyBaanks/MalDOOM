// generator.zig — Generador Classic Malbolge (Zig 0.16), espejo de meowbolge v2.
//
// Construcción por congruencia + proponente dirigido por estado:
//   op = (mem[c] + c) % 94  =>  ch = 33 + ((op - pos - 33) % 94)
// Cada candidato se acepta SOLO si el motor real (engine.zig) emite exactamente
// el objetivo. Toda la memoria interna usa arena allocator (sin frees manuales);
// el programa resultante se copia al allocator del llamador.

const std = @import("std");
const engine = @import("engine.zig");

const MOD: u16 = 94;
const LO: u8 = 33;
const HI: u8 = 126;
const MEM: usize = engine.MEM_SIZE;

const PROF_MAX: usize = 24;
const NODE_MAX: usize = 2_000_000;
const RUTAS_MAX: usize = 300;
const HAZ_MAX: usize = 60_000;

const CANDIDATAS = [_]u16{ engine.OP_ROT, engine.OP_CRAZY, engine.OP_MOVD };
const OP_ORDER = [_]u16{ engine.OP_OUT, engine.OP_ROT, engine.OP_CRAZY, engine.OP_MOVD };

/// Caracter que en la posicion `pos` se ejecuta como opcode `op`, o null.
pub fn fuentePara(op: u16, pos: usize) ?u8 {
    const v: i64 = 33 + @mod(@as(i64, op) - @as(i64, @intCast(pos)) - 33, 94);
    if (v >= 33 and v <= 126) return @intCast(v);
    return null;
}

pub fn colaHalt(pos: usize) !u8 {
    return fuentePara(engine.OP_HALT, pos) orelse error.NoHaltAtPosition;
}

fn verificaSalida(programa: []const u8, objetivo: []const u8, al: std.mem.Allocator) !bool {
    var mem: [MEM]u16 = undefined;
    const r = try engine.runInto(&mem, programa, 200_000, al);
    if (r.status != .halted) return false;
    return std.mem.eql(u8, r.output, objetivo);
}

fn rellenarCola(mem: []u16, llenado: usize) void {
    var i: usize = llenado;
    while (i < MEM) : (i += 1) {
        const prev1 = if (i >= 1) mem[i - 1] else mem[MEM - 1];
        const prev2 = if (i >= 2) mem[i - 2] else mem[MEM - 1];
        mem[i] = engine.crazyOp(prev1, prev2);
    }
}

// ---------------------------------------------------------------------------
// Proponente: BFS dirigido por estado sobre (a,d). Arena (`al`).
// ---------------------------------------------------------------------------

const Write = struct {
    address: u16,
    value: u16,
};

// A node holds only the memory cells changed by its instruction. Reads walk the
// parent chain, so every branch sees its own ROT/CRAZY and encryption effects.
const Candidate = struct {
    parent: ?*const Candidate,
    a: u16,
    d: u16,
    op: u16,
    depth: usize,
    writes: [2]Write,
    write_count: u2,
};

fn readCell(base: []const u16, node: ?*const Candidate, address: u16) u16 {
    var cursor = node;
    while (cursor) |current| {
        var i: usize = current.write_count;
        while (i > 0) {
            i -= 1;
            if (current.writes[i].address == address) return current.writes[i].value;
        }
        cursor = current.parent;
    }
    return base[address];
}

fn materializeRoute(node: *const Candidate, al: std.mem.Allocator) ![]u16 {
    var route = try al.alloc(u16, node.depth);
    var cursor: ?*const Candidate = node;
    var i = node.depth;
    while (cursor) |current| {
        if (current.parent == null) break;
        i -= 1;
        route[i] = current.op;
        cursor = current.parent;
    }
    return route;
}

fn proponerRuta(
    prefix: []const u8,
    objetivo_byte: u8,
    restrict_past: bool,
    al: std.mem.Allocator,
) !std.ArrayList([]u16) {
    var rutas = std.ArrayList([]u16).empty;

    const hal = try colaHalt(prefix.len);
    const base_len = prefix.len + 1;
    var mem: [MEM]u16 = undefined;
    for (prefix, 0..) |c, i| mem[i] = c;
    mem[prefix.len] = hal;
    rellenarCola(&mem, base_len);

    var a: u16 = 0;
    var d: u16 = 0;
    for (prefix, 0..) |_, pos| {
        const op = engine.decodeOpcode(mem[pos], @intCast(pos % MOD));
        switch (op) {
            engine.OP_ROT => {
                const v = mem[d];
                mem[d] = (v / 3) + (v % 3) * 19683;
                a = mem[d];
            },
            engine.OP_CRAZY => {
                mem[d] = engine.crazyOp(a, mem[d]);
                a = mem[d];
            },
            engine.OP_MOVD => d = mem[d],
            else => {},
        }
        if (mem[pos] >= LO and mem[pos] <= HI) mem[pos] = engine.ENCRYPT_TABLE[mem[pos] - LO];
        d = @intCast((@as(usize, d) + 1) % MEM);
    }

    const desde = prefix.len;
    var budget: usize = NODE_MAX;

    var frontier = std.ArrayList(*Candidate).empty;
    const root = try al.create(Candidate);
    root.* = .{
        .parent = null,
        .a = a,
        .d = d,
        .op = engine.OP_NOP,
        .depth = 0,
        .writes = undefined,
        .write_count = 0,
    };
    try frontier.append(al, root);
    var seen = std.AutoHashMapUnmanaged(u64, void){};
    try seen.put(al, (@as(u64, a) << 16) | d, {});

    var depth: usize = 0;
    while (depth <= PROF_MAX) : (depth += 1) {
        if (budget == 0) return rutas;
        var next = std.ArrayList(*Candidate).empty;

        for (frontier.items) |cand| {
            if (budget == 0) return rutas;
            const pos = desde + cand.depth;
            for (OP_ORDER) |op| {
                const ch = fuentePara(op, pos) orelse continue;
                if (budget == 0) return rutas;
                budget -= 1;
                var a2 = cand.a;
                var d2 = cand.d;
                var b2: ?u8 = null;
                var writes: [2]Write = undefined;
                var write_count: u2 = 1;
                const pos_address: u16 = @intCast(pos);
                const d_value = readCell(&mem, cand, cand.d);
                var pos_value: u16 = ch;
                switch (op) {
                    engine.OP_OUT => {
                        b2 = @intCast(a2 % 256);
                        if (b2.? != objetivo_byte) continue;
                    },
                    engine.OP_ROT => {
                        const v = if (cand.d == pos_address) @as(u16, ch) else d_value;
                        a2 = (v / 3) + (v % 3) * 19683;
                        if (cand.d == pos_address) {
                            pos_value = a2;
                        } else {
                            writes[1] = .{ .address = cand.d, .value = a2 };
                            write_count = 2;
                        }
                    },
                    engine.OP_CRAZY => {
                        const v = if (cand.d == pos_address) @as(u16, ch) else d_value;
                        a2 = engine.crazyOp(a2, v);
                        if (cand.d == pos_address) {
                            pos_value = a2;
                        } else {
                            writes[1] = .{ .address = cand.d, .value = a2 };
                            write_count = 2;
                        }
                    },
                    else => { // MOVD
                        const destino = if (cand.d == pos_address) @as(u16, ch) else d_value;
                        if (destino >= pos and (restrict_past or destino <= pos + PROF_MAX + 4)) {
                            continue;
                        }
                        d2 = destino;
                    },
                }
                if (pos_value >= LO and pos_value <= HI) pos_value = engine.ENCRYPT_TABLE[pos_value - LO];
                writes[0] = .{ .address = pos_address, .value = pos_value };
                const d_sig: u16 = @intCast((@as(usize, d2) + 1) % MEM);

                const next_node = try al.create(Candidate);
                next_node.* = .{
                    .parent = cand,
                    .a = a2,
                    .d = d_sig,
                    .op = op,
                    .depth = cand.depth + 1,
                    .writes = writes,
                    .write_count = write_count,
                };

                if (b2 != null and b2.? == objetivo_byte) {
                    try rutas.append(al, try materializeRoute(next_node, al));
                    if (rutas.items.len >= RUTAS_MAX) return rutas;
                } else {
                    const clave = (@as(u64, a2) << 16) | d_sig;
                    if (!seen.contains(clave)) {
                        try seen.put(al, clave, {});
                        try next.append(al, next_node);
                    }
                }
            }
        }

        if (next.items.len == 0) break;
        if (next.items.len > HAZ_MAX) next.items.len = HAZ_MAX;
        frontier = next;
    }
    return rutas;
}

// ---------------------------------------------------------------------------
// Generador experimental acotado: directo -> proponente -> bruta. Arena interna.
// Solo devuelve una fuente tras verificarla en el motor Classic; `NoRuta` es un
// resultado normal cuando el presupuesto no alcanza para una continuacion.
// ---------------------------------------------------------------------------

pub fn generar(texto: []const u8, ancho: usize, allocator: std.mem.Allocator) ![]u8 {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const al = arena.allocator();

    var fuente = std.ArrayList(u8).empty;

    for (texto, 0..) |ch, i| {
        const objetivo = texto[0 .. i + 1];
        var hallado: ?[]u8 = null;

        // 1) Directo.
        if (fuentePara(engine.OP_OUT, fuente.items.len)) |c_out| {
            var cand = std.ArrayList(u8).empty;
            try cand.appendSlice(al, fuente.items);
            try cand.append(al, c_out);
            try cand.append(al, try colaHalt(cand.items.len));
            if (try verificaSalida(cand.items, objetivo, al)) {
                cand.shrinkRetainingCapacity(cand.items.len - 1);
                hallado = try al.dupe(u8, cand.items);
            }
        }

        // 2) Rapido: proponente.
        if (hallado == null) {
            for ([_]bool{ true, false }) |restrict| {
                if (hallado != null) break;
                const rutas = try proponerRuta(fuente.items, ch, restrict, al);
                for (rutas.items) |ruta| {
                    var cand = std.ArrayList(u8).empty;
                    try cand.appendSlice(al, fuente.items);
                    var ok = true;
                    for (ruta) |op| {
                        const cc = fuentePara(op, cand.items.len) orelse {
                            ok = false;
                            break;
                        };
                        try cand.append(al, cc);
                    }
                    if (!ok) continue;
                    if (ruta[ruta.len - 1] != engine.OP_OUT) {
                        const cc = fuentePara(engine.OP_OUT, cand.items.len) orelse continue;
                        try cand.append(al, cc);
                    }
                    try cand.append(al, try colaHalt(cand.items.len));
                    if (try verificaSalida(cand.items, objetivo, al)) {
                        cand.shrinkRetainingCapacity(cand.items.len - 1);
                        hallado = try al.dupe(u8, cand.items);
                        break;
                    }
                }
            }
        }

        // 3) Bruta.
        if (hallado == null) {
            var largo: usize = 0;
            outer: while (largo < ancho) : (largo += 1) {
                var combo = std.ArrayList(u16).empty;
                try brutaRec(CANDIDATAS[0..], largo, &combo, &fuente, objetivo, &hallado, al);
                if (hallado != null) break :outer;
            }
        }

        const found = hallado orelse return error.NoRuta;
        try fuente.appendSlice(al, found);
    }

    try fuente.append(al, try colaHalt(fuente.items.len));
    return try allocator.dupe(u8, fuente.items);
}

fn brutaRec(
    opciones: []const u16,
    rest: usize,
    combo: *std.ArrayList(u16),
    fuente: *std.ArrayList(u8),
    objetivo: []const u8,
    hallado: *?[]u8,
    al: std.mem.Allocator,
) !void {
    if (rest == 0) {
        var cand = std.ArrayList(u8).empty;
        try cand.appendSlice(al, fuente.items);
        var ok = true;
        for (combo.items) |op| {
            const cc = fuentePara(op, cand.items.len) orelse {
                ok = false;
                break;
            };
            try cand.append(al, cc);
        }
        if (!ok) return;
        const cc = fuentePara(engine.OP_OUT, cand.items.len) orelse return;
        try cand.append(al, cc);
        try cand.append(al, try colaHalt(cand.items.len));
        if (try verificaSalida(cand.items, objetivo, al)) {
            cand.shrinkRetainingCapacity(cand.items.len - 1);
            hallado.* = try al.dupe(u8, cand.items);
        }
        return;
    }
    for (opciones) |op| {
        try combo.append(al, op);
        try brutaRec(opciones, rest - 1, combo, fuente, objetivo, hallado, al);
        if (hallado.* != null) return;
        _ = combo.pop();
    }
}

// ---------------------------------------------------------------------------
// CLI: malbolge-zig generate <texto>
// ---------------------------------------------------------------------------

pub fn main(init: std.process.Init) !void {
    const allocator = init.arena.allocator();

    var args_it = try std.process.Args.Iterator.initAllocator(init.minimal.args, allocator);
    defer args_it.deinit();
    var args = std.array_list.Managed([]const u8).init(allocator);
    while (args_it.next()) |arg| try args.append(arg);

    if (args.items.len < 3) {
        std.debug.print("uso: malbolge-zig generate <texto> [ancho]\n", .{});
        return;
    }
    const texto = args.items[2];
    const ancho: usize = if (args.items.len >= 4)
        std.fmt.parseInt(usize, args.items[3], 10) catch 14
    else
        14;
    const prog = try generar(texto, ancho, allocator);
    defer allocator.free(prog);

    var mem: [MEM]u16 = undefined;
    const r = try engine.runInto(&mem, prog, 2_000_000, allocator);
    defer allocator.free(r.output);
    std.debug.print("texto={s}\nceldas={d}\nejecucion={s} ({s})\n", .{ texto, prog.len, r.output, @tagName(r.status) });
    if (!std.mem.eql(u8, r.output, texto)) {
        std.debug.print("NO COINCIDE\n", .{});
        std.process.exit(1);
    }
    std.debug.print("PROGRAM={s}\n", .{prog});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test "fuente_para congruence" {
    const c = fuentePara(engine.OP_OUT, 0) orelse unreachable;
    try std.testing.expectEqual(@as(u16, 5), (c + 0) % MOD);
}

test "generate A verifies on engine" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const al = arena.allocator();
    const r = try generar("A", 6, al);
    var mem: [MEM]u16 = undefined;
    const res = try engine.runInto(&mem, r, 200_000, al);
    try std.testing.expectEqualStrings("A", res.output);
    try std.testing.expectEqual(engine.RunStatus.halted, res.status);
}

test "bounded generator reports an unsolved continuation" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const al = arena.allocator();
    try std.testing.expectError(error.NoRuta, generar("ABC", 7, al));
}
