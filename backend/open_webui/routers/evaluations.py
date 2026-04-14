from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.feedbacks import (
    FeedbackModel,
    FeedbackResponse,
    FeedbackForm,
    FeedbackUserResponse,
    FeedbackListResponse,
    FeedbackIdResponse,
    Feedbacks,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()

PAGE_ITEM_COUNT = 30


@router.get('/feedbacks/all', response_model=list[FeedbackResponse])
async def get_all_feedbacks(user=Depends(get_admin_user), db: Session = Depends(get_session)):
    feedbacks = Feedbacks.get_all_feedbacks(db=db)
    return feedbacks


@router.get('/feedbacks/all/ids', response_model=list[FeedbackIdResponse])
async def get_all_feedback_ids(user=Depends(get_admin_user), db: Session = Depends(get_session)):
    return Feedbacks.get_all_feedback_ids(db=db)


@router.delete('/feedbacks/all')
async def delete_all_feedbacks(user=Depends(get_admin_user), db: Session = Depends(get_session)):
    return Feedbacks.delete_all_feedbacks(db=db)


@router.get('/feedbacks/user', response_model=list[FeedbackUserResponse])
async def get_feedbacks_by_user(user=Depends(get_verified_user), db: Session = Depends(get_session)):
    feedbacks = Feedbacks.get_feedbacks_by_user_id(user.id, db=db)
    return feedbacks


@router.delete('/feedbacks', response_model=bool)
async def delete_feedbacks(user=Depends(get_verified_user), db: Session = Depends(get_session)):
    return Feedbacks.delete_feedbacks_by_user_id(user.id, db=db)


@router.get('/feedbacks/list', response_model=FeedbackListResponse)
async def get_feedbacks_list(
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    page = max(1, page)
    skip = (page - 1) * PAGE_ITEM_COUNT
    filter = {}
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction
    return Feedbacks.get_feedback_items(filter=filter, skip=skip, limit=PAGE_ITEM_COUNT, db=db)


@router.post('/feedback', response_model=FeedbackModel)
async def create_feedback(
    request: Request,
    form_data: FeedbackForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    feedback = Feedbacks.insert_new_feedback(user_id=user.id, form_data=form_data, db=db)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    return feedback


@router.get('/feedback/{id}', response_model=FeedbackModel)
async def get_feedback_by_id(id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)):
    if user.role == 'admin':
        feedback = Feedbacks.get_feedback_by_id(id=id, db=db)
    else:
        feedback = Feedbacks.get_feedback_by_id_and_user_id(id=id, user_id=user.id, db=db)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return feedback


@router.post('/feedback/{id}', response_model=FeedbackModel)
async def update_feedback_by_id(
    id: str,
    form_data: FeedbackForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role == 'admin':
        feedback = Feedbacks.update_feedback_by_id(id=id, form_data=form_data, db=db)
    else:
        feedback = Feedbacks.update_feedback_by_id_and_user_id(id=id, user_id=user.id, form_data=form_data, db=db)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return feedback


@router.delete('/feedback/{id}')
async def delete_feedback_by_id(id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)):
    if user.role == 'admin':
        success = Feedbacks.delete_feedback_by_id(id=id, db=db)
    else:
        success = Feedbacks.delete_feedback_by_id_and_user_id(id=id, user_id=user.id, db=db)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return success
