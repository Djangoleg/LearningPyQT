from distutils.core import setup
import py2exe

setup(
    windows=[{"script": "C:\\Users\\krole\\Documents\\GeekBrains\\LearningPyQt\\Lesson_8\\code_separation\\MyServer\\server.py"}],
    options={"py2exe": {"includes": ["PyQt5", "PyQt5.sip", "sqlalchemy"]}}
)
