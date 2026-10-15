from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PlaceReviewOverview:
    name:Optional[str] = None
    address: Optional[str] = None
    review_count: Optional[int] = None
    rating: Optional[float] = None
    keywords: Optional[dict] = field(default_factory=dict)

@dataclass
class PhotoUrls:
    thumb:Optional[str] = None
    hd: Optional[str] = None
    fhd: Optional[str] = None
    uhd: Optional[str] = None
    
@dataclass
class PlaceReviewUserProfile:
    user_google_id:Optional[int] = None
    user_name: Optional[str] = None
    user_image: Optional[PhotoUrls] = None
    user_contribution_url: Optional[str] = None
    user_review_count: Optional[int] = None
    user_photo_count: Optional[int] = None



@dataclass
class PlaceReviewPhoto:
    photo_urls: Optional[dict] =  field(default_factory=dict)
    photo_caption: Optional[str] =  None
    photo_id: Optional[str] =  None
    photo_time_relative: Optional[str] = None

@dataclass
class PlaceReviewAspectOption:
    option_key: Optional[str] = None
    option_label: Optional[str] = None

@dataclass
class PlaceReviewAspect:
    aspect_key: Optional[str] =  None
    aspect_question: Optional[str] = None
    aspect_label: Optional[str] =  None
    aspect_point: Optional[int] =  None
    aspect_option: Optional[PlaceReviewAspectOption] =  None

@dataclass
class PlaceReview:
    fid: Optional[str] = None
    review_id: Optional[str] =  None
    review_timestamp: Optional[int] =  None
    review_like_count: Optional[int] = None
    review_time_relative: Optional[str] =  None
    review_rating: Optional[float] =  None
    review_user: Optional[PlaceReviewUserProfile] =  None
    review_media: Optional[list] =  None
    review_string: Optional[str] =  None
    review_aspects: Optional[PlaceReviewAspect] = None