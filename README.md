# LearningPyQT
Способом описанным в методичке не получилось залить whl пакет на pypi. Ошибка:

Submitting dist\ok_client_messenger-0.1.tar.gz to https://upload.pypi.org/legacy/
Upload failed (400): Invalid value for blake2_256_digest. Error: Use a valid, hex-encoded, BLAKE2 message digest.
error: Upload failed (400): Invalid value for blake2_256_digest. Error: Use a valid, hex-encoded, BLAKE2 message digest.

Пошел путём описанным в https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html
с использованием пакета twine - https://twine.readthedocs.io/en/latest/

1) pip install twine
2) pip install build
3) python -m build
<!--4) twine upload -r testpypi dist/*-->
4) twine upload dist/*

Изменённый .pypirc:
[distutils] # this tells distutils what package indexes you can push to
index-servers =
  pypi
  pypitest

[pypi]
repository: https://upload.pypi.org/legacy/
username: okr 
password: xxxxxxxxxxxx

[pypitest]
repository:  https://test.pypi.org/legacy/
username: okr 
password: xxxxxxxxxxxx
