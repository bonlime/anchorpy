from __future__ import annotations

from ast import literal_eval
from pathlib import Path
from typing import Any

from anchorpy_idl import Idl, IdlType, IdlTypeSimple
from anchorpy.clientgen.common import _add_generated_file_header, _sanitize


BASE_TEMPLATE = """\
from __future__ import annotations

import typing

import msgspec
from construct import Container
from anchorpy.coder.accounts import ACCOUNT_DISCRIMINATOR_SIZE
from anchorpy.error import AccountInvalidDiscriminator


class BaseTypeDecoder(msgspec.Struct, gc=False):
    discriminator: typing.ClassVar[bytes]
    layout: typing.ClassVar[typing.Any]

    @classmethod
    def from_decoded(cls, obj: Container):
        raise NotImplementedError()

    @classmethod
    def decode(cls, data: bytes):
        disc = getattr(cls, "discriminator", None)
        if disc is not None:
            if data[:ACCOUNT_DISCRIMINATOR_SIZE] != disc:
                raise AccountInvalidDiscriminator(
                    "The discriminator for this account is invalid"
                )
            data = data[ACCOUNT_DISCRIMINATOR_SIZE:]
        layout = getattr(cls, "layout", None)
        if layout is None or len(data) == 0:
            return cls()
        decoded = layout.parse(data)
        return cls.from_decoded(decoded)


class InstructionData(BaseTypeDecoder, gc=False):
    pass


class AccountData(BaseTypeDecoder, gc=False):
    pass


class EventData(BaseTypeDecoder, gc=False):
    pass
"""


def gen_base(root: Path) -> None:
    (root / "base.py").write_text(_add_generated_file_header(BASE_TEMPLATE))


def _format_const_value(const_type: IdlType, const_value: Any) -> str:
    raw_value = const_value
    if isinstance(raw_value, str):
        try:
            raw_value = literal_eval(raw_value)
        except Exception:
            pass

    if const_type == IdlTypeSimple.Bytes:
        if isinstance(raw_value, (bytes, bytearray, memoryview)):
            return repr(bytes(raw_value))
        if isinstance(raw_value, list) and all(
            isinstance(b, int) and 0 <= b <= 255 for b in raw_value
        ):
            return repr(bytes(raw_value))
    if isinstance(raw_value, int) and not isinstance(raw_value, bool):
        return f"{raw_value:_}"
    if isinstance(raw_value, list):
        return repr(raw_value)
    return repr(raw_value)


def gen_constants(idl: Idl, program_id: str, root: Path) -> None:
    lines = [
        "from __future__ import annotations",
        "",
        "from solders.pubkey import Pubkey",
        "",
        f'PROGRAM_ID = Pubkey.from_string("{program_id}")',
    ]

    for const in idl.constants:
        const_name = _sanitize(const.name)
        value_literal = _format_const_value(const.ty, const.value)
        lines.append(f"{const_name} = {value_literal}")
    code = "\n".join(lines) + "\n"
    (root / "constants.py").write_text(_add_generated_file_header(code))
