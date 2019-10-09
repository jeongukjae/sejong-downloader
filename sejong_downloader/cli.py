import argparse
import asyncio
import re
from typing import Generator

import aiofiles
import aiohttp

SEJONG_CORPUS_DOWNLOAD_LINK = "https://ithub.korean.go.kr/user/total/database/corpusList.do"
SEJONG_CORPUS_DOWNLOAD_PARAMS = {"boardSeq": 2, "userId": 0, "pageUnit": 10000}

parser = argparse.ArgumentParser()
parser.add_argument("command", help="download, merge", choices=["download", "merge"])


def main():
    args = parser.parse_args()
    if args.command == "download":
        asyncio.run(_download_sejong_corpus())
    elif args.command == "merge":
        _merge_corpus()
    else:
        raise ValueError(f"Command '{args.command}' is not supported command.")


async def _download_sejong_corpus():
    async with aiohttp.ClientSession() as session:
        indexing_page_content = _fetch_indexing_page(session)
        print("fetched indexing page")
        article_list = _extract_article_list_from(indexing_page_content)

        await asyncio.gather(*(_save_article(article, session) for article in article_list))


def _merge_corpus():
    pass


class Article:
    def __init__(self, article_num, article_sequence, title):
        self.article_num = article_num
        self.article_sequence = article_sequence
        self.title = title

    def __repr__(self):
        return f"<Article num{self.article_num} {self.title} at {self.article_sequence}>"


def _fetch_indexing_page(session: aiohttp.ClientSession) -> str:
    return open("./test.html").read()
    # rv = requests.get(SEJONG_CORPUS_DOWNLOAD_LINK, params=SEJONG_CORPUS_DOWNLOAD_PARAMS)
    # if rv.status != 200:
    #     raise ValueError("Cannot fetch Sejong Corpus Page")

    # return rv.text


def _extract_article_list_from(indexing_page_content: str) -> Generator[Article, None, None]:
    pattern = re.compile(
        r"<tr.*\n"
        r"[ \t]*<td[^>]*>([\d]*).+\n"
        r"[ \t]*<td[^>]*>\n"
        r"[ \t]*\n"
        r"[ \t]*<a href=\"javascript:goView\('([\d]*)'\)\".*\n"
        r"[ \t]*(.*)\n",
        re.MULTILINE,
    )
    for item in pattern.finditer(indexing_page_content):
        yield Article(*item.groups())


async def _save_article(article: Article, session: aiohttp.ClientSession):
    file_content = await _download_file_from(article, session)
    print(f"download {article}")
    async with aiofiles.open(f"./data/test_{article.article_num}.txt", "wb") as f:
        f.write(file_content)


async def _download_file_from(article: Article, session: aiohttp.ClientSession):
    article_content = await _fetch_article(article, session)
    attachment_id = _get_attachment_id_from(article_content)

    print(f"start to download {article}")
    async with session.post(
        "https://ithub.korean.go.kr/common/boardFileDownload.do",
        data={
            "articleSeq": article.article_sequence,
            "fNo": article.article_sequence,
            "attachIdx": attachment_id,
            "fileSeq": "1",
            "userId": "0",
            "boardSeq": "2",
            "boardType": "CORPUS",
        },
    ) as response:
        if response.status != 200:
            raise ValueError(f"Cannot donwload {article}")

        return await response.read()


async def _fetch_article(article: Article, session: aiohttp.ClientSession):
    async with session.get(
        "https://ithub.korean.go.kr/user/total/database/corpusView.do",
        params={**SEJONG_CORPUS_DOWNLOAD_PARAMS, "articleSeq": article.article_sequence},
    ) as response:

        if response.status != 200:
            raise ValueError(f"Cannot fetch article {article}")

        return await response.text()


def _get_attachment_id_from(article_content):
    pattern = re.compile(r"<input type=\"hidden\" id=\"attachIdx\" name=\"attachIdx\" value=\"([^\"]*)\"/>")
    attachment_ids = pattern.findall(article_content)

    if len(attachment_ids) != 1:
        raise ValueError("Length of attachment id should be 1")

    return attachment_ids[0]
