#!/usr/bin/env python3
"""Top Shop's LZSS (MAIN 8001a8a8): Okumura's, a 4 KB window zeroed and written from 0xfee,
flag bit 1 = literal, 0 = a 12-bit window offset and a 4-bit length (+3). A block starts
with its own size as a u32 (header included), then the flag and data bytes."""
import struct


def decompress(buf, pos=0):
    end = min(pos + struct.unpack_from('<I', buf, pos)[0], len(buf))
    win = bytearray(4096)
    r = 0xfee
    out = bytearray()
    p = pos + 4
    while p < end:
        flags = buf[p] | 0xff00; p += 1
        while flags & 0x100:
            if flags & 1:
                if p >= end: return bytes(out)
                c = buf[p]; p += 1
                out.append(c); win[r] = c; r = (r + 1) & 0xfff
            else:
                if p + 2 > end: return bytes(out)
                lo, hi = buf[p], buf[p + 1]; p += 2
                off = lo | (hi & 0xf0) << 4
                for i in range((hi & 0xf) + 3):
                    c = win[(off + i) & 0xfff]
                    out.append(c); win[r] = c; r = (r + 1) & 0xfff
            flags >>= 1
    return bytes(out)


def compress(data):
    """Greedy LZSS that the game's decoder reads back exactly. Returns the block with its
    size header."""
    N, F, TH = 4096, 18, 2
    win = bytearray(N)
    r = 0xfee
    out = bytearray()
    i = 0
    # index of window positions by 3-byte prefix, refreshed as we go (plain search is fine
    # at these file sizes)
    while i < len(data):
        flagpos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= len(data): break
            best_len, best_off = 0, 0
            maxlen = min(F, len(data) - i)
            if maxlen > TH:
                # candidate window positions: every position in the window (the decoder copies
                # byte by byte, so overlaps with the bytes being written are allowed)
                for back in range(1, N - F + 1):
                    s = (r - back) & 0xfff
                    if win[s] != data[i]: continue
                    l = 0
                    # simulate the decoder copying from the ring
                    tmp = {}
                    while l < maxlen:
                        sp = (s + l) & 0xfff
                        c = tmp.get(sp, win[sp]) if sp not in range(r, r) else None
                        c = tmp[sp] if sp in tmp else win[sp]
                        if c != data[i + l]: break
                        tmp[(r + l) & 0xfff] = data[i + l]
                        l += 1
                    if l > best_len:
                        best_len, best_off = l, s
                        if l == maxlen: break
            if best_len > TH:
                out += bytes([best_off & 0xff, (best_off >> 4) & 0xf0 | (best_len - 3)])
                n = best_len
            else:
                flags |= 1 << bit
                out.append(data[i]); n = 1
            for k in range(n):
                win[r] = data[i + k]; r = (r + 1) & 0xfff
            i += n
        out[flagpos] = flags
    return struct.pack('<I', len(out) + 4) + bytes(out)
