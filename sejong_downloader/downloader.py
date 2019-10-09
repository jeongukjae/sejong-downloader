import asyncio
import os
import re
from typing import Generator, Optional, Union

import aiofiles
import aiohttp

from .logger import logger

SEJONG_ARTICLE_INDEXING_LINK = "https://ithub.korean.go.kr/user/total/database/corpusList.do"
SEJONG_ARTICLE_LINK = "https://ithub.korean.go.kr/user/total/database/corpusView.do"
SEJONG_DOWNLOAD_LINK = "https://ithub.korean.go.kr/common/boardFileDownload.do"
SEJONG_ZIP_DOWNLOAD_LINK = "https://ithub.korean.go.kr/common/boardFileZipDownload.do"
SEJONG_DEFAULT_REQUEST_PARAMS = {"boardSeq": 2, "userId": 0, "pageUnit": 10000}
SEJONG_DOWNLOAD_REQUEST_PARAMS = {
    **SEJONG_DEFAULT_REQUEST_PARAMS,
    "fileSeq": "1",
    "userId": "0",
    "boardSeq": "2",
    "boardType": "CORPUS",
}

SEJONG_FILE_CATEGORIES = {"orgFileSeq": "1", "posFileSeq": "2", "semFileSeq": "3", "synFileSeq": "4"}

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

    os.makedirs(base_path, exist_ok=True)
    os.makedirs(os.path.join(base_path, "cached"), exist_ok=True)

    async with aiohttp.ClientSession() as session:
        indexing_caching_path = os.path.join(base_path, "cached", "indexing.html")
        indexing_page_content = await _get_cached(indexing_caching_path)
        if indexing_page_content is None:
            indexing_page_content = await _fetch_indexing_page(session, base_path)
            await _cache_to(indexing_page_content, indexing_caching_path)

        article_list = _extract_article_list_from(indexing_page_content)

        logger.debug("trigger async coroutines for save article data")
        await asyncio.gather(*(_save_attachements_in_article(base_path, article, session) for article in article_list))


async def _get_cached(path: str) -> Optional[str]:
    if os.path.exists(path) and os.path.getsize(path) != 0:
        logger.debug(f"restore cache from {path}")
        async with aiofiles.open(path, "r") as f:
            return await f.read()
    else:
        return None


async def _cache_to(content: Union[bytes, str], path: str) -> None:
    async with aiofiles.open(path, "wb" if isinstance(content, bytes) else "w") as f:
        logger.debug(f"cache to {path}")
        await f.write(content)


async def _fetch_indexing_page(session: aiohttp.ClientSession, base_path: str) -> str:
    logger.info("fetching indexing page")
    async with session.get(SEJONG_ARTICLE_INDEXING_LINK, params=SEJONG_DEFAULT_REQUEST_PARAMS) as response:
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
    caching_path = os.path.join(base_path, "cached", f"article_{article.article_num}.html")
    article_content = await _get_cached(caching_path)
    if article_content is None:
        logger.info(f"fetch article {article}")
        article_content = await _fetch_article(article, session)
        await _cache_to(article_content, caching_path)

    attachment_id = _get_attachment_id_from(article_content)
    file_sequence_value = _get_file_sequence_values_from(article_content)

    corpus_path = os.path.join(
        base_path, f"test_{article.article_num}_corpus.{'zip' if ',' in file_sequence_value else 'text'}"
    )
    if os.path.exists(corpus_path) and os.path.getsize(corpus_path) != 0:
        logger.debug(f"skip to download {article}")
        return

    logger.debug(f"start to download {article} ({file_sequence_value})")
    async with session.post(
        SEJONG_ZIP_DOWNLOAD_LINK if "," in file_sequence_value else SEJONG_DOWNLOAD_LINK,
        data={
            **SEJONG_DOWNLOAD_REQUEST_PARAMS,
            "articleSeq": article.article_sequence,
            "fNo": article.article_sequence,
            "attachIdx": attachment_id,
            "fileSeqValues": file_sequence_value,
        },
    ) as response:
        if response.status != 200:
            raise ValueError(f"Cannot donwload {article} / {response.status} {await response.text()}")
        await _save_articles_attachment(corpus_path, await response.read())


async def _fetch_article(article: Article, session: aiohttp.ClientSession) -> str:
    async with session.get(
        SEJONG_ARTICLE_LINK, params={**SEJONG_DEFAULT_REQUEST_PARAMS, "articleSeq": article.article_sequence}
    ) as response:
        if response.status != 200:
            raise ValueError(f"Cannot fetch article {article}")

        return await response.text()


def _get_attachment_id_from(article_content: str) -> str:
    pattern = re.compile(r"<input type=\"hidden\" id=\"attachIdx\" name=\"attachIdx\" value=\"([^\"]*)\"/>")
    attachment_ids = pattern.findall(article_content)

    if len(attachment_ids) != 1:
        raise ValueError("Length of attachment ids should be 1")

    return attachment_ids[0]


def _get_file_sequence_values_from(article_content: str) -> str:
    pattern = re.compile(f'<input type="checkbox" name="(.*FileSeq)"')
    seq_values = pattern.findall(article_content)

    converted_seq_values = [SEJONG_FILE_CATEGORIES[seq] for seq in seq_values if seq in SEJONG_FILE_CATEGORIES]

    return ",".join(converted_seq_values)


async def _save_articles_attachment(path: str, content: bytes) -> None:
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)

