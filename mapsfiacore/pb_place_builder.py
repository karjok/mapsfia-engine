from typing import Optional


def build_place_pb(
    place_identifier: str,
    search_query: str,
    *,
    map_distance: float,
    map_longitude: float,
    map_latitude: float,
    viewport_latitude: float,
    viewport_longitude: float,
    session_token: str,
    display_query: str = "",
) -> str:
    return (
        f"!1m17"
        f"!1s{place_identifier}"
        f"!3m12"
        f"!1m3!1d{map_distance}!2d{map_longitude}!3d{map_latitude}"
        f"!2m3!1f0!2f0!3f0"
        f"!3m2!1i713!2i933!4f13.1"
        f"!4m2!3d{viewport_latitude}!4d{viewport_longitude}"
        f"!6s{search_query}"
        f"!12m4!2m3!1i360!2i120!4i8"
        f"!13m57"
        f"!2m2!1i203!2i100"
        f"!3m2!2i4!5b1"
        f"!6m6!1m2!1i86!2i86!1m2!1i408!2i240"
        f"!7m33"
        f"!1m3!1e1!2b0!3e3"
        f"!1m3!1e2!2b1!3e2"
        f"!1m3!1e2!2b0!3e3"
        f"!1m3!1e8!2b0!3e3"
        f"!1m3!1e10!2b0!3e3"
        f"!1m3!1e10!2b1!3e2"
        f"!1m3!1e10!2b0!3e4"
        f"!1m3!1e9!2b1!3e2"
        f"!2b1!9b0"
        f"!15m8"
        f"!1m7!1m2!1m1!1e2"
        f"!2m2!1i195!2i195!3i20"
        f"!14m2!1s{session_token}!7e81"
        f"!15m111"
        f"!1m29!4e2"
        f"!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1"
        f"!18m17!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1"
        f"!20b1!21b1!22b1!30b1!32b1"
        f"!33m1!1b1!34b1!36e2"
        f"!10m1!8e3!11m1!3e1!17b1"
        f"!20m2!1e3!1e6"
        f"!24b1!25b1!26b1!27b1!29b1!30m1!2b1"
        f"!36b1!37b1"
        f"!39m3!2m2!2i1!3i1"
        f"!43b1!52b1!54m1!1b1!55b1!56m1!1b1"
        f"!61m2!1m1!1e1"
        f"!65m5!3m4!1m3!1m2!1i224!2i298"
        f"!72m22"
        f"!1m8!2b1!5b1!7b1"
        f"!12m4!1b1!2b1!4m1!1e1!4b1"
        f"!8m10!1m6"
        f"!4m1!1e1!4m1!1e3!4m1!1e4"
        f"!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts"
        f"!6m1!1e1!9b1!89b1"
        f"!90m2!1m1!1e2"
        f"!98m3!1b1!2b1!3b1"
        f"!103b1"
        f"!113b1"
        f"!114m3!1b1!2m1!1b1"
        f"!117b1"
        f"!122m1!1b1"
        f"!126b1!127b1"
        f"!128m1!1b1"
        f"!21m0"
        f"!22m2!1e81!8e4"
        f"!29m0"
        f"!30m6!3b1!6m1!2b1!7m1!2b1!9b1"
        f"!34m5!7b1!10b1!14b1!15m1!1b0"
        f"!37i797"
        f"!39s{display_query}"
        f"!41b1"
    )
