"""Access control utilities"""
from fastapi import HTTPException, status
from auth import User


def check_video_access(video_data: dict, user: User) -> None:
    """
    Check if user has access to video.
    Raises HTTPException if access denied.
    """
    video_owner_id = video_data.get("user_id")

    # If no owner (legacy data), allow access
    if not video_owner_id:
        return

    # Check if user owns the video
    if video_owner_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this video"
        )


def associate_video_with_user(video_data: dict, user: User, user_videos: dict) -> None:
    """Associate video with user for access control"""
    video_data["user_id"] = user.user_id

    # Track user's videos
    if user.user_id not in user_videos:
        user_videos[user.user_id] = []

    if video_data["video_id"] not in user_videos[user.user_id]:
        user_videos[user.user_id].append(video_data["video_id"])
