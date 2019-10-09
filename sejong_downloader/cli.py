import argparse
import asyncio

from .downloader import download_sejong_corpus

parser = argparse.ArgumentParser()
parser.add_argument("command", help="download, merge", choices=["download", "merge"])

parser.add_argument("-o", "--out", type=str, help="세종 코퍼스가 저장될 base path", default="./data", required=False)


def main():
    args = parser.parse_args()
    if args.command == "download":
        asyncio.run(download_sejong_corpus(args.out))
    elif args.command == "merge":
        pass
    else:
        raise ValueError(f"Command '{args.command}' is not supported command.")
