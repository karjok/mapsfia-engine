## Place item
have 260 field (0-259)
- 4[7] = Rating/review count
- 7 = website = 7[0] url, 7[1] = domain
- 10 = FID
- 11 = Place name
- 13 = Place type
- 18 = address full
- 30 = Timezone
- 31 = review overview
- 39 = address
- 42 = preview url
- 49 = is claimed
- 51 = images
- 76 = place type id
- 78 = place_id
- 88 = place type
- 89 = kgmid
- 100 = services, amenities, facilities
- 149 = plus code
- 153 = review keywords
- 154 = descriptions
- 175 = Reviews
    14 fields (0-13):
        - 9 = reviewer list and its review data
            





- 178 = Phones
- 183 = All address fields
- 203 = Opening Hours
- 208 = latitude, longitude
- 243 = Country


## Review item:
6 fileds (0-5):
    - 0 = review_id
    - 1 = review metadata
        16 fileds:
            - 2, 3 = review timestamp
            - 4 = reviewer profile data
                6 fileds:
                    - 2[0] = contibutions URL
                    - 5 = contibutor metadata
                        11 fields:
                            - 0 = contributor name
                            - 1 = contributor profile picture
                            - 2[0] = photos contributions URL
                            - 3 = contributor profile ID
                            - 5 = review  count
                            - 6 = photo count
                            - 8[1] = local guide level
                            - 9 = rating count
            - 6 = relative time of his review
    - 2 = review data
        16 fileds:
            - 0[0] = star count
            - 2 = review photos
                - 0
            - 6 = review aspects
                7 fields:
                    review aspect data fileds:
                        16 fileds:
                        - 0[0] = aspect_key
                        - 1 = aspect label strings
                        - 2 = the answer for this aspect:
                            - 0[0][0] = asnwer fileds (6 fileds):
                                - 0[0] = answer_key
                                - 1 = answer label strings
                                - 4 = answer relative strings
                        - 5 = aspect label
                        - 11[0] = aspect point count
            - 14 = review translations
                - 0, 1 = translation_id_key
                - 2,3 = translation label string
            - 15 = review translation strings metadata:
                fileds count based on 14 key count with each field:
                    - 0 = string on translation translation_id_key


## Photos
photo object have 4 fileds:
    - 0 = photo id
    - 1 = photo data field:
        have 44 fileds:
            - 0 = photo id
            - 6[0] = photo url
            - 6[2][0] = photo width
            - 6[2][1] = photo hight
            - 8[0][1] = longitude
            - 8[0][2] = latitude
            - 21[3][5][0] = photo descriptions
            - 21[6][8] = post date


## Suggestion

23 fields:
- 22 = suggestion item data
    42 fields:
        - 13[0] = fid
        - 13[1] = Label
        - 13[3][2] = lat
        - 13[3][3] = lon
        - 13[10] = gmid
        - 22[1][0] = name
        - 22[7][2][0] = type code