import re
pb = input("PB: ")
tokens = pb.split("!")
"""
m = pesan (angka = jumlah token di dalamnya), s = string, d = double, f = float, i = integer, e = enum, b = boolean.
"""
field_patt = re.compile(r"(\d+[msdfieb]{1})")
for idx, i in enumerate(tokens, start=1):
    fmat = re.match(field_patt, i)
    if fmat:
        fmat = fmat.group(1)
    else:
        fmat = ""
    val = re.sub(field_patt,"",i)
    print(f"{idx: <6}{i: <6}, {fmat}")