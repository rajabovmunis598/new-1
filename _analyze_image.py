import zlib, struct
from collections import Counter

import os
d = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image.png'), 'rb').read()
assert d[:8] == b'\x89PNG\r\n\x1a\n'
pos = 8
idat = b''
w = h = None
while pos < len(d):
    ln = struct.unpack('>I', d[pos:pos+4])[0]
    typ = d[pos+4:pos+8]
    dat = d[pos+8:pos+8+ln]
    if typ == b'IHDR':
        w, h, bd, ct = struct.unpack('>IIBB', dat[:10])
        print('size', w, h, 'bitdepth', bd, 'colortype', ct, 'interlace', dat[11])
        if ct not in (2, 6):
            raise SystemExit('unsupported colortype')
    elif typ == b'IDAT':
        idat += dat
    elif typ == b'IEND':
        break
    pos += 12 + ln

raw = zlib.decompress(idat)
bpp = 4 if ct == 6 else 3
stride = w * bpp
pic = bytearray(w * h * 3)

pos = 0
prev2 = bytearray(stride)
for y in range(h):
    f = raw[pos]
    row_raw = raw[pos+1:pos+1+stride]
    pos += stride + 1
    out = bytearray(stride)
    for x in range(stride):
        a = out[x-bpp] if x >= bpp else 0
        b = prev2[x]
        c = prev2[x-bpp] if x >= bpp else 0
        pp = a + b - c
        pa = abs(pp - a); pb = abs(pp - b); pc = abs(pp - c)
        if pa <= pb and pa <= pc:
            pr = a
        elif pb <= pc:
            pr = b
        else:
            pr = c
        if f == 1: v = (row_raw[x] + a) & 255
        elif f == 2: v = (row_raw[x] + b) & 255
        elif f == 3: v = (row_raw[x] + (a + b) // 2) & 255
        elif f == 4: v = (row_raw[x] + pr) & 255
        else: v = row_raw[x]
        out[x] = v
    for x in range(w):
        base = x * bpp
        pic[(y*w + x)*3] = out[base]
        pic[(y*w + x)*3 + 1] = out[base+1]
        pic[(y*w + x)*3 + 2] = out[base+2]
    prev2 = out

# Resize to 120x120 grid and count dominant colors
gw, gh = 120, 120
cnt = Counter()
for gy in range(gh):
    for gx in range(gw):
        sx0 = gx * w // gw; sx1 = (gx+1) * w // gw
        sy0 = gy * h // gh; sy1 = (gy+1) * h // gh
        rs = gs = bs = n = 0
        for sy in range(sy0, sy1, max(1, (sy1-sy0)//3)):
            for sx in range(sx0, sx1, max(1, (sx1-sx0)//3)):
                i = (sy*w + sx)*3
                rs += pic[i]; gs += pic[i+1]; bs += pic[i+2]; n += 1
        cnt[(rs//n//32*32, gs//n//32*32, bs//n//32*32)] += 1

print('Dominant color blocks (quantized to 32):')
for color, n in cnt.most_common(18):
    print(color, n)

# Row profile: average color per 30-row band
print('\nRow bands (avg RGB per 5%% height):')
for b in range(20):
    sy0 = b * h // 20; sy1 = (b+1) * h // 20
    rs = gs = bs = n = 0
    for sy in range(sy0, sy1, max(1, (sy1-sy0)//5)):
        for sx in range(0, w, max(1, w//80)):
            i = (sy*w + sx)*3
            rs += pic[i]; gs += pic[i+1]; bs += pic[i+2]; n += 1
    print(f'{b*5:2d}-{(b+1)*5:2d}%: ({rs//n}, {gs//n}, {bs//n})')