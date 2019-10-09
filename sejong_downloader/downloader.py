import asyncio
import os
import re
from typing import Generator

import aiofiles
import aiohttp

from .logger import logger

SEJONG_CORPUS_ARTICLE_INDEXING_LINK = "https://ithub.korean.go.kr/user/total/database/corpusList.do"
SEJONG_CORPUS_ARTICLE_LINK = "https://ithub.korean.go.kr/user/total/database/corpusView.do"
SEJONG_CORPUS_DOWNLOAD_LINK = "https://ithub.korean.go.kr/common/boardFileDownload.do"
SEJONG_CORPUS_DEFAULT_REQUEST_PARAMS = {"boardSeq": 2, "userId": 0, "pageUnit": 10000}
SEJONG_CORPUS_DOWNLOAD_REQUEST_PARAMS = {
    **SEJONG_CORPUS_DEFAULT_REQUEST_PARAMS,
    "fileSeq": "1",
    "userId": "0",
    "boardSeq": "2",
    "boardType": "CORPUS",
}

__all__ = ["download_sejong_corpus"]


class Article:
    def __init__(self, article_num: str, article_sequence: str, title: str):
        self.article_num = article_num.strip()
        self.article_sequence = article_sequence.strip()
        self.title = title.strip()

    def __repr__(self):
        return f"<Article num{self.article_num} {self.title} at {self.article_sequence}>"


async def download_sejong_corpus(base_path: str) -> None:
    """세종 코퍼스 전체를 base_path로 다운로드한다."""
    async with aiohttp.ClientSession() as session:
        logger.info("fetching indexing page")
        indexing_page_content = await _fetch_indexing_page(session)
        article_list = _extract_article_list_from(indexing_page_content)

        logger.debug("trigger async coroutines for save article data")
        await asyncio.gather(
            *(
                _save_attachements_in_article(base_path, article, session)
                for article in article_list
                if "폐회사_한세추, 전자전사자료" in article.title
            )
        )


async def _fetch_indexing_page(session: aiohttp.ClientSession) -> str:
    async with session.get(
        SEJONG_CORPUS_ARTICLE_INDEXING_LINK, params=SEJONG_CORPUS_DEFAULT_REQUEST_PARAMS
    ) as response:
        if response.status != 200:
            raise ValueError("Cannot fetch Sejong Corpus Page")

        return await response.text()


def _extract_article_list_from(indexing_page_content: str) -> Generator[Article, None, None]:
    pattern = re.compile(
        r"<tr.*\n"
        r"[ \t]*<td[^>]*>([\d]*).+\n"
        r".*\n"
        r".*\n"
        r"[ \t]*<a href=\"javascript:goView\('([\d]*)'.*\n"
        r"[ \t]*(.*)",
        re.MULTILINE,
    )

    for item in pattern.finditer(indexing_page_content):
        yield Article(*item.groups())


async def _save_attachements_in_article(base_path: str, article: Article, session: aiohttp.ClientSession) -> None:
    logger.info(f"fetch article {article}")
    article_content = await _fetch_article(article, session)
    async with aiofiles.open(os.path.join(base_path, f"test_{article.article_num}.data"), "w") as f:
        await f.write(article_content)

    attachment_id = _get_attachment_id_from(article_content)

    logger.debug(f"start to download {article}")
    async with session.post(
        SEJONG_CORPUS_DOWNLOAD_LINK,
        data={
            **SEJONG_CORPUS_DOWNLOAD_REQUEST_PARAMS,
            "articleSeq": article.article_sequence,
            "fNo": article.article_sequence,
            "attachIdx": attachment_id,
        },
    ) as response:
        if response.status != 200:
            raise ValueError(f"Cannot donwload {article}")

        await _save_articles_attachment(
            os.path.join(base_path, f"test_{article.article_num}_corpus.data"), await response.read()
        )


async def _fetch_article(article: Article, session: aiohttp.ClientSession) -> str:
    async with session.get(
        SEJONG_CORPUS_ARTICLE_LINK,
        params={**SEJONG_CORPUS_DEFAULT_REQUEST_PARAMS, "articleSeq": article.article_sequence},
    ) as response:

        if response.status != 200:
            raise ValueError(f"Cannot fetch article {article}")

        return await response.text()


def _get_attachment_id_from(article_content) -> str:
    pattern = re.compile(r"<input type=\"hidden\" id=\"attachIdx\" name=\"attachIdx\" value=\"([^\"]*)\"/>")
    attachment_ids = pattern.findall(article_content)

    if len(attachment_ids) != 1:
        raise ValueError("Length of attachment ids should be 1")

    return attachment_ids[0]


async def _save_articles_attachment(path: str, content: bytes) -> None:
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)
