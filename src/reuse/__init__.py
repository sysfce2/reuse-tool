# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
# SPDX-FileCopyrightText: 2021 Alliander N.V.
# SPDX-FileCopyrightText: 2023 Carmen Bianca BAKKER <carmenbianca@fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""reuse is a tool for compliance with the REUSE recommendations.

Although the API is documented, it is **NOT** guaranteed stable between minor or
even patch releases. The semantic versioning of this program pertains
exclusively to the reuse CLI command. If you want to use reuse as a Python
library, you should pin reuse to an exact version.

Having given the above disclaimer, the API has been relatively stable
nevertheless, and we (the maintainers) do make some efforts to not needlessly
change the public API.
"""

# TODO: When Python 3.9 is dropped, consider using `type | None` instead of
# `Optional[type]`.

import gettext
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Optional

from boolean.boolean import Expression
from license_expression import Licensing

try:
    __version__ = version("reuse")
except PackageNotFoundError:
    # package is not installed
    __version__ = "5.0.0"

__author__ = "Carmen Bianca Bakker"
__email__ = "carmenbianca@fsfe.org"
__license__ = "Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND GPL-3.0-or-later"
__REUSE_version__ = "3.3"

_LOGGER = logging.getLogger(__name__)

_LICENSING = Licensing()


class SourceType(Enum):
    """
    An enumeration representing the types of sources for license information.
    """

    #: A .license file containing license information.
    DOT_LICENSE = "dot-license"
    #: A file header containing license information.
    FILE_HEADER = "file-header"
    #: A .reuse/dep5 file containing license information.
    DEP5 = "dep5"
    #: A REUSE.toml file containing license information.
    REUSE_TOML = "reuse-toml"


# TODO: In Python 3.10+, add kw_only=True
@dataclass(frozen=True)
class ReuseInfo:
    """Simple dataclass holding licensing and copyright information"""

    spdx_expressions: set[Expression] = field(default_factory=set)
    copyright_lines: set[str] = field(default_factory=set)
    contributor_lines: set[str] = field(default_factory=set)
    path: Optional[str] = None
    source_path: Optional[str] = None
    source_type: Optional[SourceType] = None

    def _check_nonexistent(self, **kwargs: Any) -> None:
        nonexistent_attributes = set(kwargs) - set(self.__dict__)
        if nonexistent_attributes:
            raise KeyError(
                f"The following attributes do not exist in"
                f" {self.__class__}: {', '.join(nonexistent_attributes)}"
            )

    def copy(self, **kwargs: Any) -> "ReuseInfo":
        """Return a copy of ReuseInfo, replacing the values of attributes with
        the values from *kwargs*.
        """
        self._check_nonexistent(**kwargs)
        new_kwargs = {}
        for key, value in self.__dict__.items():
            new_kwargs[key] = kwargs.get(key, value)
        return self.__class__(**new_kwargs)  # type: ignore

    def union(self, value: "ReuseInfo") -> "ReuseInfo":
        """Return a new instance of ReuseInfo where all set attributes are equal
        to the union of the set in *self* and the set in *value*.

        All non-set attributes are set to their values in *self*.

        >>> one = ReuseInfo(copyright_lines={"Jane Doe"}, source_path="foo.py")
        >>> two = ReuseInfo(copyright_lines={"John Doe"}, source_path="bar.py")
        >>> result = one.union(two)
        >>> print(sorted(result.copyright_lines))
        ['Jane Doe', 'John Doe']
        >>> print(result.source_path)
        foo.py
        """
        new_kwargs = {}
        for key, attr_val in self.__dict__.items():
            if isinstance(attr_val, set) and (other_val := getattr(value, key)):
                new_kwargs[key] = attr_val.union(other_val)
            else:
                new_kwargs[key] = attr_val
        return self.__class__(**new_kwargs)  # type: ignore

    def contains_copyright_or_licensing(self) -> bool:
        """Either *spdx_expressions* or *copyright_lines* is non-empty."""
        return bool(self.spdx_expressions or self.copyright_lines)

    def contains_copyright_xor_licensing(self) -> bool:
        """One of *spdx_expressions* or *copyright_lines* is non-empty."""
        return bool(self.spdx_expressions) ^ bool(self.copyright_lines)

    def contains_info(self) -> bool:
        """Any field except *path*, *source_path* and *source_type* is
        non-empty.
        """
        keys = {
            key
            for key in self.__dict__
            if key not in ("path", "source_path", "source_type")
        }
        return any(self.__dict__[key] for key in keys)

    def __bool__(self) -> bool:
        return any(self.__dict__.values())

    def __or__(self, value: "ReuseInfo") -> "ReuseInfo":
        return self.union(value)
