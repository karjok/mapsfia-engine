"""
Membangun parameter `pb` Google Maps (endpoint /maps/preview/place) dari data dinamis.

Bagian dinamis : fid (feature id), lat/lng, query, label, kgmid (opsional), token sesi
Bagian statis  : seluruh blok !12m4 ... !37i797 (setting UI/klien) -> STATIC_BODY
Counter `mN`   : dihitung otomatis (jumlah token anak termasuk turunannya)

CATATAN: endpoint ini tidak resmi & melanggar ToS jika di-scrape masif.
Untuk produksi gunakan Google Places API (New). Skrip ini untuk eksplorasi.
"""
import base64
import json
import os
import struct
import urllib.parse
import urllib.request

# ---------- bagian STATIC (identik di semua URL contoh) ----------
STATIC_VIEW = "!2m3!1f0!2f0!3f0!3m2!1i713!2i933!4f13.1"

STATIC_BODY = (
    "!12m4!2m3!1i360!2i120!4i8!13m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86"
    "!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8"
    "!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2"
    "!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20"
    "!14m2!1s{token}!7e81"
    "!15m111!1m29!4e2!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m17!3b1!4b1!5b1"
    "!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!30b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3"
    "!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1"
    "!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1"
    "!65m5!3m4!1m3!1m2!1i224!2i298"
    "!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4"
    "!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts"
    "!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1"
    "!117b1!122m1!1b1!126b1!127b1!128m1!1b1!21m0!22m2!1e81!8e4!29m0"
    "!30m6!3b1!6m1!2b1!7m1!2b1!9b1!34m5!7b1!10b1!14b1!15m1!1b0!37i797"
)


# ---------- helper ----------
def _count(tokens):
    """Jumlah token '!' (untuk field mN)."""
    return len(tokens)


def fid_to_chij(fid: str) -> str:
    """'0xAAAA:0xBBBB' -> ChIJ... (place_id). Dua uint64 little-endian dalam protobuf."""
    a, b = (int(x, 16) for x in fid.split(":"))
    raw = b"\x0a\x12\x09" + struct.pack("<Q", a) + b"\x11" + struct.pack("<Q", b)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def random_token() -> str:
    """Token sesi (!14m2!1s...). Nilai asli berbasis waktu; acak biasanya diterima."""
    return base64.urlsafe_b64encode(os.urandom(17)).decode().rstrip("=")[:23]


def build_place_pb(fid, lat, lng, query="", label="", kgmid=None,
             view_lat=None, view_lng=None, altitude=77081.5, token=None):
    """
    fid   : '0x2e69930018eb511f:0x18cbb95276f3d78d'  (WAJIB, identitas tempat)
    lat/lng : koordinat tempat target (!4m2!3d !4d)
    query : teks pencarian (!6s) ; label : nama tempat (!39s)
    kgmid : '/g/11zd56d0xm' (opsional -> memakai varian !1m22 seperti URL warkop)
    """
    fid = fid.replace("%3A", ":")
    view_lat = lat if view_lat is None else view_lat
    view_lng = lng if view_lng is None else view_lng
    token = token or random_token()
    q = urllib.parse.quote(query, safe="+")

    view = f"!3m12!1m3!1d{altitude}!2d{view_lng}!3d{view_lat}{STATIC_VIEW}"
    target = f"!4m2!3d{lat}!4d{lng}"
    body = STATIC_BODY.replace("{token}", token)

    if kgmid:  # varian dengan identitas lengkap (kgmid + ChIJ)
        ident = (f"!15m4!1m3!1s{fid}!4s{urllib.parse.quote(kgmid, safe='')}"
                 f"!5s{fid_to_chij(fid)}")
    else:
        ident = ""

    inner = f"!1s{fid}{view}{target}{ident}"
    n = _count([t for t in inner.split("!") if t])  # hitung token anak
    pb = f"!1m{n}{inner}!6s{q}{body}"
    if label:
        pb += f"!39s{urllib.parse.quote_plus(label)}"
    pb += "!41b1"
    return pb


def build_place_url(fid, lat, lng, query="", label="", hl="id", gl="id", **kw):
    pb = build_place_pb(fid, lat, lng, query, label, **kw)
    return ("https://www.google.com/maps/preview/place?authuser=0"
            f"&hl={hl}&gl={gl}&pb={pb}&q={urllib.parse.quote(query or label)}")


# ---------- fetch & parse ----------
def _g(obj, *path):
    for p in path:
        try:
            obj = obj[p]
        except (IndexError, KeyError, TypeError):
            return None
    return obj



if __name__ == "__main__":
    # contoh: Warkop Agusta (dari URL referensi ke-3)
    FID = "0x2e69930b461b0663:0x5319eeba2a7036c5"
    print(build_url(FID, -6.317656899999999, 106.9805255, "", "Kedai ajib Bang eja",
                    kgmid="/g/11hz1nm5h6"))
    # data = fetch_place(FID, -6.3247032, 106.9684572, "warkop", "Warkop Agusta", kgmid="/g/11zd56d0xm")
    # print(summarize(data))
