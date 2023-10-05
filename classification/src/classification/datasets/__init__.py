from pathlib import Path
from typing import List, Tuple


def get_cls_from_path(file: Path) -> str:
    """
    Returns a sound class from a given path.

    By convention, sound files should be named `some/path/cls_index.format`,
    where format can be any supported audio format, index is some
    unique number for that class,
    and cls is the class name.

    :param file: The file path.
    :return: The class name.
    """
    return file.stem.split("_", maxsplit=1)[0]


class Dataset:
    def __init__(
        self, folder: Path = Path(__file__).parent / "soundfiles", format: str = "wav"
    ):
        """
        Initializes a dataset from a given folder, including
        subfolders. Uses :func:`get_cls_from_path` to determine
        the sound class of each file.

        :param folder: Where to find the soundfiles.
        :param format: The sound files format, use
            `'*'` to include all formats.
        """
        files = {}

        for file in folder.glob("**/*." + format):
            cls = get_cls_from_path(file)
            files.setdefault(cls, []).append(file)

        self.files = files

    def __getitem__(self, cls_index: Tuple[str, int]) -> Path:
        """
        Returns the file path corresponding the
        the (class name, index) pair.

        :cls_index: Class name and index.
        :return: The file path.
        """
        cls, index = cls_index
        return self.files[cls][index]

    def list_classes(self) -> List[str]:
        """
        Returns the list of classes
        in the given dataset.

        :return: The list of classes.
        """
        return list(self.files.keys())
