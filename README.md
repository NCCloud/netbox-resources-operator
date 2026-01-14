# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/NCCloud/netbox-resources-operator/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                |    Stmts |     Miss |   Cover |   Missing |
|-------------------- | -------: | -------: | ------: | --------: |
| app/\_\_init\_\_.py |        0 |        0 |    100% |           |
| app/conditions.py   |       24 |       24 |      0% |      1-90 |
| app/config.py       |       18 |        0 |    100% |           |
| app/crd.py          |       20 |       20 |      0% |      6-96 |
| app/errors.py       |        4 |        0 |    100% |           |
| app/handlers.py     |       22 |       22 |      0% |      1-50 |
| app/kubernetes.py   |       25 |        0 |    100% |           |
| app/metrics.py      |       44 |       27 |     39% |53-75, 79-80, 89-101 |
| app/models.py       |      122 |        0 |    100% |           |
| app/netbox.py       |       33 |        1 |     97% |        13 |
| app/netboxobject.py |      228 |       10 |     96% |85-86, 201, 233, 260, 322, 424, 436, 442, 561 |
| app/operator.py     |       57 |       57 |      0% |     1-124 |
| app/util.py         |       24 |        0 |    100% |           |
| **TOTAL**           |  **621** |  **161** | **74%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/NCCloud/netbox-resources-operator/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/NCCloud/netbox-resources-operator/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/NCCloud/netbox-resources-operator/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/NCCloud/netbox-resources-operator/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FNCCloud%2Fnetbox-resources-operator%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/NCCloud/netbox-resources-operator/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.