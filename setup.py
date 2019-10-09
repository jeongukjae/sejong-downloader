from setuptools import find_packages, setup

setup(
    name="sejong-downloader",
    version="0.0.1",
    description="Downloader for Sejong corpus",
    url="https://github.com/jeongukjae/sejong-downloader",
    install_requires=["requests"],
    author="Jeong Ukjae",
    author_email="jeongukjae@gmail.com",
    packages=find_packages(exclude=["tests"]),
)
