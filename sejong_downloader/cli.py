import argparse
import asyncio

from .downloader import download_sejong_corpus

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", type=str, help="세종 코퍼스가 저장될 base path", default="./data", required=False)


def main():
    args = parser.parse_args()
    asyncio.run(download_sejong_corpus(args.path))
