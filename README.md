# py404

py404 is a CLI tool for checking if your website has suffered from deadlinks/linkrot. It checks for 404s on all kinds of links: hrefs, imgs, scripts in <head>, etc. 

It was a fun way to learn some asyncio.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install py404. It requires Python >=3.9.

```shell
$ pip install py404
```

## Usage

Type `py404` followed by the URL you want to check. Add `--save` to save the output as a csv.

```shell
$ py404 https://example.com
```

## License

Made by [Will](https://github.com/WillDenby) and released under the [MIT](https://choosealicense.com/licenses/mit/) License