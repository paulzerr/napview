from setuptools import setup

install_requires = [
    "scipy>=1.17.0,<1.18",
    "numpy>=2.3.4,<2.4",
    "mne==1.8.0",
    "Flask==3.0.3",
    "peewee==3.17.6",
    "pylsl==1.16.2",
    "setuptools",
    "edfio==0.4.3",
    "joblib==1.4.2",
    "pandas==2.2.3",
    "numba>=0.63.1,<0.64",
    "antropy==0.1.9",
    "lightgbm==4.6.0",
    "psg_utils",
    "nidra",
]

setup(
    install_requires=install_requires,
)
