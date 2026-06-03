"""评审模块数据库操作层"""
from typing import Any

from sqlalchemy import ColumnElement, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_eval.entity.do.eval_do import EvalProject, EvalReview, EvalOpinion, EvalMaterial
from module_eval.entity.vo.eval_vo import EvalProjectModel, EvalProjectPageQuery, EvalReviewModel
from utils.page_util import PageUtil


class EvalProjectDao:
    """评审项目 DAO"""

    @classmethod
    async def get_project_list(
        cls, db: AsyncSession, query_object: EvalProjectPageQuery, data_scope_sql: ColumnElement, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(EvalProject)
            .where(
                EvalProject.project_name.like(f'%{query_object.project_name}%') if query_object.project_name else True,
                data_scope_sql,
            )
            .order_by(desc(EvalProject.create_time))
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_project_by_id(cls, db: AsyncSession, project_id: int) -> EvalProject | None:
        result = await db.execute(select(EvalProject).where(EvalProject.project_id == project_id))
        return result.scalars().first()

    @classmethod
    async def add_project(cls, db: AsyncSession, project: EvalProjectModel) -> EvalProject:
        db_model = EvalProject(**project.model_dump(exclude_unset=True))
        db.add(db_model)
        await db.flush()
        return db_model

    @classmethod
    async def update_project(cls, db: AsyncSession, project: dict) -> None:
        from sqlalchemy import update
        await db.execute(update(EvalProject), [project])

    @classmethod
    async def delete_project(cls, db: AsyncSession, project_id: int) -> None:
        from sqlalchemy import delete
        await db.execute(delete(EvalProject).where(EvalProject.project_id == project_id))


class EvalReviewDao:
    """评审记录 DAO"""

    @classmethod
    async def get_review_list(
        cls, db: AsyncSession, query_object: EvalReviewModel, data_scope_sql: ColumnElement, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(EvalReview)
            .where(
                EvalReview.project_id == query_object.project_id if query_object.project_id else True,
                data_scope_sql,
            )
            .order_by(desc(EvalReview.create_time))
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_review_by_id(cls, db: AsyncSession, review_id: int) -> EvalReview | None:
        result = await db.execute(select(EvalReview).where(EvalReview.review_id == review_id))
        return result.scalars().first()

    @classmethod
    async def add_review(cls, db: AsyncSession, review: dict) -> EvalReview:
        db_model = EvalReview(**review)
        db.add(db_model)
        await db.flush()
        return db_model

    @classmethod
    async def update_review(cls, db: AsyncSession, review_id: int, data: dict) -> None:
        from sqlalchemy import update
        await db.execute(update(EvalReview).where(EvalReview.review_id == review_id), [data])


class EvalOpinionDao:
    """评审意见 DAO"""

    @classmethod
    async def get_opinions_by_review(cls, db: AsyncSession, review_id: int) -> list[EvalOpinion]:
        result = await db.execute(
            select(EvalOpinion).where(EvalOpinion.review_id == review_id).order_by(EvalOpinion.sort_order)
        )
        return list(result.scalars().all())

    @classmethod
    async def add_opinions(cls, db: AsyncSession, opinions: list[dict]) -> None:
        for op in opinions:
            db.add(EvalOpinion(**op))
        await db.flush()
