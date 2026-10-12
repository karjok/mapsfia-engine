from curl_cffi import Session
import json
from models.models import Suggestion
from mapsfiacore.pb_place import build_url
# from review_parser import parse_reviews
from utils.utils import get_candidate_from_data, normalize_raw_response

sess = Session(impersonate="chrome131")

# place detail
place1 = "https://www.google.com/maps/preview/place?authuser=0&hl=en&gl=id&pb=!1m24!1s0x2e6993de7b979ff7%3A0xdba6773feff87672!3m12!1m3!1d19270.058364121665!2d106.96956929282548!3d-6.32365203290457!2m3!1f0!2f0!3f0!3m2!1i713!2i933!4f13.1!4m2!3d-6.3330625!4d106.9671875!15m6!1m5!1s0x2e6993de7b979ff7%3A0xdba6773feff87672!4s%2Fg%2F11yfpzk10q!5sChIJ95-Xe96TaS4Rcnb47z93pts!6s8321726113463817396!7s109984875029556749868!6sWarkop+Warmindo!12m4!2m3!1i360!2i120!4i8!13m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!14m2!1sbj7BatvzBsSx4-EPtIXOyQk!7e81!15m111!1m29!4e2!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m17!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!30b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!21m0!22m2!1e81!8e4!29m0!30m6!3b1!6m1!2b1!7m1!2b1!9b1!34m5!7b1!10b1!14b1!15m1!1b0!37i797!38sCg9XYXJrb3AgV2FybWluZG9aESIPd2Fya29wIHdhcm1pbmRvkgEEY2FmZZoBRENpOURRVWxSUVVOdlpFTm9kSGxqUmpsdlQyNU9WVlp1VW5wbFZWRXhWbXN3ZUdJeWNHdFJiRTR6WVZSQ2RsVXlZeEFC4AEA-gEECDcQIA!39sWARJON+-+Kota+Wisata!41b1&q=WARJON%20-%20Kota%20Wisata"
place2 = "https://www.google.com/maps/preview/place?authuser=0&hl=en&gl=id&pb=!1m22!1s0x2e6993b6453ca1f3%3A0x7308506cc407700a!3m12!1m3!1d19270.059961456853!2d106.9695263743517!3d-6.323609175748073!2m3!1f0!2f0!3f0!3m2!1i713!2i933!4f13.1!4m2!3d-6.3416622!4d106.9817946!15m4!1m3!1s0x2e6993b6453ca1f3%3A0x7308506cc407700a!4s%2Fg%2F11dym8d8zp!5sChIJ86E8RbaTaS4RCnAHxGxQCHM!6sWarkop+Warmindo!12m4!2m3!1i360!2i120!4i8!13m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!14m2!1sbj7BatvzBsSx4-EPtIXOyQk!7e81!15m111!1m29!4e2!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m17!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!30b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!21m0!22m2!1e81!8e4!29m0!30m6!3b1!6m1!2b1!7m1!2b1!9b1!34m5!7b1!10b1!14b1!15m1!1b0!37i797!38sCg9XYXJrb3AgV2FybWluZG9aESIPd2Fya29wIHdhcm1pbmRvkgETcG9ycmlkZ2VfcmVzdGF1cmFudJoBJENoZERTVWhOTUc5blMwVkpRMEZuU1VOeWEzVmxVV2xuUlJBQuABAPoBBAgAEEM!39sWARKOP+77+Termuda!41b1&q=WARKOP%2077%20Termuda"
place3 = "https://www.google.com/maps/preview/place?authuser=0&hl=en&gl=id&pb=!1m24!1s0x2e6989380fffa71d%3A0xb31daf149b643791!3m12!1m3!1d77081.40167110915!2d106.98116769140988!3d-6.315811299125076!2m3!1f0!2f0!3f0!3m2!1i713!2i933!4f13.1!4m2!3d-6.2462295!4d106.99206219999999!15m6!1m5!1s0x2e6989380fffa71d%3A0xb31daf149b643791!4s%2Fg%2F11b6rl6_dy!5sChIJHaf_DziJaS4RkTdkmxSvHbM!6s14975555602807004598!7s105127080678625302497!6sHotels!12m4!2m3!1i360!2i120!4i8!13m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!14m2!1sB23BatGyPMbG4-EPiMPbkAc!7e81!15m122!1m40!4e1!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!17m9!1m3!1i2026!2i10!3i5!2m3!1i2026!2i10!3i6!4i0!18m17!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!30b1!32b1!33m1!1b1!34b1!36e2!22BQ2hrSW5iRWtFaE1JOHZuT2o5LWVsd01WRXd6X0NCMzBndzlP!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!21m0!22m2!1e81!8e4!29m0!30m7!3b1!4b1!6m1!2b1!7m1!2b1!9b1!34m5!7b1!10b1!14b1!15m1!1b0!37i797!38sCgZIb3RlbHOSAQVob3RlbKoBOhABKgoiBmhvdGVscygAMh4QASIainsixGVQ51rDIRxGAWYdQunD1rZjbCyu2qAyChACIgZob3RlbHPgAQA!39sAston+Imperial+Bekasi+Hotel+%26+Conference+Center!41b1&q=Aston%20Imperial%20Bekasi%20Hotel%20%26%20Conference%20Center"
place4 = "https://www.google.com/maps/preview/place?authuser=0&hl=en&gl=id&pb=!1m22!1s0x2e69930018eb511f%3A0x18cbb95276f3d78d!3m12!1m3!1d77081.45344626361!2d106.98082426846969!3d-6.315463574233818!2m3!1f0!2f0!3f0!3m2!1i713!2i933!4f13.1!4m2!3d-6.3247032!4d106.96845719999999!15m4!1m3!1s0x2e69930018eb511f%3A0x18cbb95276f3d78d!4s%2Fg%2F11zd56d0xm!5sChIJH1HrGACTaS4RjdfzdlK5yxg!6swarkop!12m4!2m3!1i360!2i120!4i8!13m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!14m2!1sD27BatflFv-WnesPhfedkAM!7e81!15m111!1m29!4e2!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m17!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!30b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!21m0!22m2!1e81!8e4!29m0!30m6!3b1!6m1!2b1!7m1!2b1!9b1!34m5!7b1!10b1!14b1!15m1!1b0!37i797!38sCgZ3YXJrb3CSAQtjb2ZmZWVfc2hvcOABAA!39sWarkop+Agusta!41b1&q=Warkop%20Agusta"
#search
url3 = "https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=id&pb=!4m12!1m3!1d77081.29811222863!2d106.94683561639165!3d-6.316506749272517!2m3!1f0!2f0!3f0!3m2!1i1121!2i933!4f13.1!7i20!10b1!12m26!1m5!18b1!30b1!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1!16b1!17m1!3e1!20m4!5e2!6b1!8b1!14b1!46m1!1b0!96b1!99b1!19m4!2m3!1i360!2i120!4i8!20m65!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m16!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!22m6!1smj3BatnDJ8mQ4-EPg-C5iA0%3A809!2s1i%3A0%2Ct%3A11887%2Cp%3Amj3BatnDJ8mQ4-EPg-C5iA0%3A809!7e81!12e3!17smj3BatnDJ8mQ4-EPg-C5iA0%3A851!18e15!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i933!1m6!1m2!1i1071!2i0!2m2!1i1121!2i933!1m6!1m2!1i0!2i0!2m2!1i1121!2i20!1m6!1m2!1i0!2i913!2m2!1i1121!2i933!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!31b1!37m1!1e81!42b1!47m0!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!9b1!10e2!50m4!2e2!3m2!1b1!3b1!67m5!7b1!10b1!14b1!15m1!1b0!69i797!77b1&q=Warkop%20Warmindo&oq=Warkop%20Warmindo&gs_l=maps.12...0.0.3.590767.0.0.....0.0..0.....0......maps..0.0.0.0.&tch=1&ech=5&psi=mj3BatnDJ8mQ4-EPg-C5iA0.1791049116225.1"
search2 = "https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=id&pb=!4m12!1m3!1d77081.27222072272!2d106.94700732786161!3d-6.316680611885405!2m3!1f0!2f0!3f0!3m2!1i1121!2i933!4f13.1!7i20!10b1!12m26!1m5!18b1!30b1!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1!16b1!17m1!3e1!20m4!5e2!6b1!8b1!14b1!46m1!1b0!96b1!99b1!19m4!2m3!1i360!2i120!4i8!20m65!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m16!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!22m6!1smj3BatnDJ8mQ4-EPg-C5iA0%3A1400!2s1i%3A0%2Ct%3A11886%2Cp%3Amj3BatnDJ8mQ4-EPg-C5iA0%3A1400!7e81!12e5!17smj3BatnDJ8mQ4-EPg-C5iA0%3A1443!18e15!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i933!1m6!1m2!1i1071!2i0!2m2!1i1121!2i933!1m6!1m2!1i0!2i0!2m2!1i1121!2i20!1m6!1m2!1i0!2i913!2m2!1i1121!2i933!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!31b1!37m1!1e81!42b1!47m0!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!9b1!10e2!50m4!2e2!3m2!1b1!3b1!67m5!7b1!10b1!14b1!15m1!1b0!69i797!77b1&q=laundy&oq=laundy&gs_l=maps.3..38i426k1l5.7885.8831.4.9582.6.6.....144.522.0j4.4.....0....1..maps..2.4.543.0..38i39k1j38i377k1.&tch=1&ech=6&psi=mj3BatnDJ8mQ4-EPg-C5iA0.1791049116225.1"
# suggestion
url4 = "https://www.google.com/s?tbm=map&gs_ri=maps&suggest=p&authuser=0&hl=en&gl=id&psi=mj3BatnDJ8mQ4-EPg-C5iA0.1791054619671.1&q=Warkop+Warmindo&ech=1&pb=!2i0!4m12!1m3!1d77081.27222072272!2d106.94700732786161!3d-6.316680611885405!2m3!1f0!2f0!3f0!3m2!1i1121!2i933!4f13.1!7i20!10b1!12m26!1m5!18b1!30b1!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1!16b1!17m1!3e1!20m4!5e2!6b1!8b1!14b1!46m1!1b0!96b1!99b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!22m3!1smj3BatnDJ8mQ4-EPg-C5iA0!7e81!17smj3BatnDJ8mQ4-EPg-C5iA0%3A870!23m2!4b1!10b1!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!26m4!2m3!1i80!2i92!4i8!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!31b1!37m1!1e81!47m0!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!9b1!10e2!61b1!67m5!7b1!10b1!14b1!15m1!1b0!69i797!77b1"
url5 = "https://www.google.com/s?tbm=map&gs_ri=maps&suggest=p&authuser=0&hl=en&gl=id&psi=mj3BatnDJ8mQ4-EPg-C5iA0.1791054619671.1&q=batam&ech=7&pb=!2i5!4m12!1m3!1d77081.27222072272!2d106.94700732786161!3d-6.316680611885405!2m3!1f0!2f0!3f0!3m2!1i1121!2i933!4f13.1!7i20!10b1!12m26!1m5!18b1!30b1!31m1!1b1!34e1!2m4!5m1!6e2!20e3!39b1!10b1!12b1!13b1!16b1!17m1!3e1!20m4!5e2!6b1!8b1!14b1!46m1!1b0!96b1!99b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m33!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!1m3!1e9!2b1!3e2!2b1!9b0!15m8!1m7!1m2!1m1!1e2!2m2!1i195!2i195!3i20!22m3!1smj3BatnDJ8mQ4-EPg-C5iA0!7e81!17smj3BatnDJ8mQ4-EPg-C5iA0%3A1389!23m2!4b1!10b1!24m109!1m27!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m16!3b1!4b1!5b1!6b1!9b1!13b1!14b1!17b1!20b1!21b1!22b1!32b1!33m1!1b1!34b1!36e2!10m1!8e3!11m1!3e1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!27b1!29b1!30m1!2b1!36b1!37b1!39m3!2m2!2i1!3i1!43b1!52b1!54m1!1b1!55b1!56m1!1b1!61m2!1m1!1e1!65m5!3m4!1m3!1m2!1i224!2i298!72m22!1m8!2b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!4b1!8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_google_review_posts__and__hotel_and_vr_partner_review_posts!6m1!1e1!9b1!89b1!90m2!1m1!1e2!98m3!1b1!2b1!3b1!103b1!113b1!114m3!1b1!2m1!1b1!117b1!122m1!1b1!126b1!127b1!128m1!1b1!26m4!2m3!1i80!2i92!4i8!34m19!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!23b1!25b1!26b1!31b1!37m1!1e81!47m0!49m10!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!9b1!10e2!61b1!67m5!7b1!10b1!14b1!15m1!1b0!69i797!77b1"

def get_response(url):
    headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "available-dictionary": ":7+SR5NB8qv2v+Wvwi15vwRoVb/4bMsMh2QjOSpKvNeY=:",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not=A?Brand\";v=\"99\", \"Brave\";v=\"151\", \"Chromium\";v=\"151\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Linux\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "x-maps-diversion-context-bin": "CAE="
  }
    r = sess.get(url, headers=headers)
    return r.text

def process_suggestions_response(data:list)-> list[Suggestion]:
    TYPE_KIND = {
        445: "country",
        446: "state/province",
        444: "city/town",
        429: "district",
        426: "place",
        384: "village",
        72:  "poi",
    }
    # suggestions items are 2 iter from root
    sugest_items = get_candidate_from_data(data, iter_count=2)
    suggestion_results = []
    for sug_place in sugest_items:
        sugg = get_candidate_from_data(sug_place)
        name = sugg[1][0]
        address = sugg[2][0]
        d = sugg[13][0]
        fid = d[0]
        label = d[1]
        lat, lon = sugg[11][2:]
        kind = sugg[7][2][0]
        mid = d[10]
        suggestion_results.append(
            Suggestion(
                fid,
                label,
                mid,
                lat,
                lon,
                name=name,
                address=address,
                type_code=kind,
                kind=TYPE_KIND[kind]
            )
        )
    return suggestion_results


def process_search_response(data:list):
    search_items = get_candidate_from_data(data)
    for item in search_items:
        p = get_candidate_from_data(item)
        # print(json.dumps(p))
        print("="*100)

def process_place_response(data:list):
    details = get_candidate_from_data(data)
    print(details[4])

url = build_url(
    "0x2e6992435fe439ff:0x900432035b09e05a",
    -6.3196012, 106.9727561, "", "Kedai Kingkit Coffe N Food", kgmid="/g/11dz2yxjnz", hl="id", gl="id")
print(url)
r = get_response(url)
rj = normalize_raw_response(r)
# data = get_candidate_from_data(rj)
process_place_response(rj)
