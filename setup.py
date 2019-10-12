from setuptools import find_packages, setup

with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="sejong-downloader",
    version="1.0.0",
    description="Downloader for Sejong corpus",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jeongukjae/sejong-downloader",
    install_requires=["aiohttp", "aiofiles"],
    author="Jeong Ukjae",
    author_email="jeongukjae@gmail.com",
    packages=find_packages(exclude=["tests"]),
    entry_points={"console_scripts": ["sejong-downloader = sejong_downloader.cli:main"]},
)
