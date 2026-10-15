#!/usr/bin/env py
"""
MALDOOM Ternary Capsule Encoder/Decoder
Serializa estado del juego <-> array de palabras de 10 trits (0..59048)
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# ─── Constants ──────────────────────────────────────────────────────────────
MAX_TRIT10 = 59048  # 3^10 - 1
MAGIC = 0xDEAD  # 57005
VERSION = 1

# crazy operation for checksum
CRAZY_TBL = [
    [1, 0, 0],
    [1, 0, 2],
    [2, 2, 1]
]

def crazy_op(a: int, b: int) -> int:
    """Operación crazy ternaria sobre 10 trits."""
    result = 0
    mult = 1
    aa, bb = a, b
    for _ in range(10):
        result += CRAZY_TBL[bb % 3][aa % 3] * mult
        aa //= 3
        bb //= 3
        mult *= 3
    return result

# ─── RNG Trinario ───────────────────────────────────────────────────────────
class TritRNG:
    """LCG ternario: state = (state * 21 + 7) % 59049"""
    def __init__(self, seed: int = 1):
        self.state = seed % 59049
        self.counter = 0
    
    def next_trit(self) -> int:
        self.state = (self.state * 21 + 7) % 59049
        self.counter = (self.counter + 1) % 59049
        return self.state % 3
    
    def next_int(self, max_val: int) -> int:
        """Genera entero 0..max_val-1 usando trits."""
        # Usar rechazo para distribución uniforme
        while True:
            val = 0
            mult = 1
            for _ in range(10):  # 10 trits = 0..59048
                val += self.next_trit() * mult
                mult *= 3
            if val < max_val:
                return val

# ─── Capsule Structure ──────────────────────────────────────────────────────

@dataclass
class PlayerState:
    x: int = 0          # 0..59048
    y: int = 0
    z: int = 0
    angle: int = 0      # 0..65535 mapped to 0..59048
    health: int = 100
    armor: int = 0
    ammo_shells: int = 50
    ammo_cells: int = 300
    ammo_rockets: int = 5
    weapons_bitmask: int = 0x3  # fist + pistol
    keys_bitmask: int = 0
    selected_weapon: int = 1
    pending_weapon: int = 1
    player_flags: int = 0
    attack_state: int = 0

@dataclass
class WorldState:
    doors: List[int] = field(default_factory=list)      # packed states
    switches: List[int] = field(default_factory=list)
    pickups: List[int] = field(default_factory=list)
    enemies: List[int] = field(default_factory=list)
    projectiles: List[int] = field(default_factory=list)

@dataclass
class EngineState:
    scripts_running: int = 0
    rng_counter: int = 0

@dataclass
class TernaryCapsule:
    magic: int = MAGIC
    version: int = VERSION
    tick: int = 0
    rng_state: int = 1
    player: PlayerState = field(default_factory=PlayerState)
    world: WorldState = field(default_factory=WorldState)
    engine: EngineState = field(default_factory=EngineState)
    checksum: int = 0

    # ─── Encode/Decode ────────────────────────────────────────────────────
    
    def to_words(self) -> List[int]:
        """Serializa a lista de palabras de 10 trits."""
        words = [
            self.magic,
            self.version,
            self.tick,
            self.rng_state,
            # Player
            self.player.x,
            self.player.y,
            self.player.z,
            self.player.angle,
            self.player.health,
            self.player.armor,
            self.player.ammo_shells,
            self.player.ammo_cells,
            self.player.ammo_rockets,
            self.player.weapons_bitmask,
            self.player.keys_bitmask,
            self.player.selected_weapon,
            self.player.pending_weapon,
            self.player.player_flags,
            self.player.attack_state,
        ]
        
        # World - doors
        words.append(len(self.world.doors))
        words.extend(self.world.doors[:64])
        # Pad to 64
        while len(words) < 20 + 64:
            words.append(0)
        
        # World - switches
        words.append(len(self.world.switches))
        words.extend(self.world.switches[:64])
        while len(words) < 20 + 64 + 1 + 64:
            words.append(0)
        
        # World - pickups
        words.append(len(self.world.pickups))
        words.extend(self.world.pickups[:128])
        while len(words) < 20 + 64 + 1 + 64 + 1 + 128:
            words.append(0)
        
        # World - enemies
        words.append(len(self.world.enemies))
        words.extend(self.world.enemies[:64])
        while len(words) < 20 + 64 + 1 + 64 + 1 + 128 + 1 + 64:
            words.append(0)
        
        # World - projectiles
        words.append(len(self.world.projectiles))
        words.extend(self.world.projectiles[:32])
        while len(words) < 20 + 64 + 1 + 64 + 1 + 128 + 1 + 64 + 1 + 32:
            words.append(0)
        
        # Engine
        words.append(self.engine.scripts_running)
        words.append(self.engine.rng_counter)
        
        # Compute checksum
        checksum = 0
        for w in words:
            checksum = crazy_op(checksum, w)
        words.append(checksum % 59049)
        
        return words
    
    @classmethod
    def from_words(cls, words: List[int]) -> 'TernaryCapsule':
        """Deserializa desde lista de palabras."""
        if len(words) < 23:
            raise ValueError(f"Capsule too short: {len(words)} words")
        
        if words[0] != MAGIC:
            raise ValueError(f"Invalid magic: {words[0]:#x} != {MAGIC:#x}")
        
        capsule = cls(
            magic=words[0],
            version=words[1],
            tick=words[2],
            rng_state=words[3],
        )
        
        # Player (words 4-18)
        p = capsule.player
        p.x, p.y, p.z, p.angle = words[4], words[5], words[6], words[7]
        p.health, p.armor = words[8], words[9]
        p.ammo_shells, p.ammo_cells, p.ammo_rockets = words[10], words[11], words[12]
        p.weapons_bitmask, p.keys_bitmask = words[13], words[14]
        p.selected_weapon, p.pending_weapon = words[15], words[16]
        p.player_flags, p.attack_state = words[17], words[18]
        
        # World - parse variable sections
        idx = 19
        
        # Doors
        num_doors = words[idx]; idx += 1
        capsule.world.doors = words[idx:idx+num_doors]; idx += 64
        
        # Switches
        num_switches = words[idx]; idx += 1
        capsule.world.switches = words[idx:idx+num_switches]; idx += 64
        
        # Pickups
        num_pickups = words[idx]; idx += 1
        capsule.world.pickups = words[idx:idx+num_pickups]; idx += 128
        
        # Enemies
        num_enemies = words[idx]; idx += 1
        capsule.world.enemies = words[idx:idx+num_enemies]; idx += 64
        
        # Projectiles
        num_projectiles = words[idx]; idx += 1
        capsule.world.projectiles = words[idx:idx+num_projectiles]; idx += 32
        
        # Engine
        capsule.engine.scripts_running = words[idx]; idx += 1
        capsule.engine.rng_counter = words[idx]; idx += 1
        
        # Checksum
        capsule.checksum = words[idx] if idx < len(words) else 0
        
        # Verify checksum
        computed = 0
        for w in words[:-1]:
            computed = crazy_op(computed, w)
        if computed % 59049 != capsule.checksum:
            raise ValueError(f"Checksum mismatch: computed {computed%59049}, stored {capsule.checksum}")
        
        return capsule
    
    def verify_checksum(self) -> bool:
        words = self.to_words()
        computed = 0
        for w in words[:-1]:
            computed = crazy_op(computed, w)
        return computed % 59049 == words[-1]

# ─── Test ───────────────────────────────────────────────────────────────────

def test_capsule():
    # Create test capsule
    capsule = TernaryCapsule(
        tick=12345,
        rng_state=42,
        player=PlayerState(
            x=1234, y=5678, z=999,
            angle=32768,  # 180 degrees
            health=75, armor=50,
            ammo_shells=40, ammo_cells=200, ammo_rockets=3,
            weapons_bitmask=0x1F, keys_bitmask=0x3,
        ),
        world=WorldState(
            doors=[0x123, 0x456],
            switches=[0x789],
            pickups=[0xAA, 0xBB, 0xCC],
            enemies=[0x1111, 0x2222],
            projectiles=[0x333],
        ),
        engine=EngineState(scripts_running=0x5, rng_counter=100),
    )
    
    # Encode
    words = capsule.to_words()
    print(f"Capsule size: {len(words)} words = {len(words)*10} trits = {len(words)*10/8:.0f} bytes")
    print(f"First 20 words: {words[:20]}")
    print(f"Checksum: {words[-1]}")
    print(f"Verify: {capsule.verify_checksum()}")
    
    # Decode
    decoded = TernaryCapsule.from_words(words)
    print(f"\nDecoded tick: {decoded.tick}")
    print(f"Decoded player: x={decoded.player.x}, y={decoded.player.y}, health={decoded.player.health}")
    print(f"Decoded world: doors={len(decoded.world.doors)}, enemies={len(decoded.world.enemies)}")
    print(f"Checksum valid: {decoded.verify_checksum()}")
    
    # Verify roundtrip
    words2 = decoded.to_words()
    print(f"Roundtrip match: {words == words2}")
    
    # SHA256 for evidence
    data = b''.join(w.to_bytes(2, 'little') for w in words)  # 10 trits fit in 16 bits
    sha = hashlib.sha256(data).hexdigest()
    print(f"SHA256: {sha}")

if __name__ == "__main__":
    test_capsule()