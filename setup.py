import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rockblox",
    version="0.0.1",
    author="h0nda",
    author_email="1@1.com",
    description="Roblox wrapper, with support for the game client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/h0nde/rockblox",
    packages=setuptools.find_packages(),
    classifiers=[
    ],
    install_requires=[
       'pywin32',
       'pillow'
    ]
    python_requires='>=3.6',
)
