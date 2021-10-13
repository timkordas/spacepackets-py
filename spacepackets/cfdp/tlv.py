from __future__ import annotations
from typing import Tuple, Optional
import enum
from spacepackets.log import get_console_logger
from spacepackets.cfdp.lv import CfdpLv


class TlvTypes(enum.IntEnum):
    """All available TLV types"""
    FILESTORE_REQUEST = 0x00
    FILESTORE_RESPONSE = 0x01
    MESSAGE_TO_USER = 0x02
    FAULT_HANDLER = 0x04
    FLOW_LABEL = 0x05
    ENTITY_ID = 0x06


class FilestoreActionCode(enum.IntEnum):
    """All filestore action codes as specified in CCSDS 727.0-B-5 p.86
    SNP: Second name present, SNN: Second name not present"""
    CREATE_FILE_SNM = 0b0000
    DELETE_FILE_SNN = 0b0001
    RENAME_FILE_SNP = 0b0010
    APPEND_FILE_SNP = 0b0011
    REPLACE_FILE_SNP = 0b0100
    CREATE_DIR_SNN = 0b0101
    REMOVE_DIR_SNN = 0b0110
    DENY_FILE_SMM = 0b0111
    DENY_DIR_SNN = 0b1000


class FilestoreResponseStatusCode(enum.IntEnum):
    """File store response status codes. First four bits are the action code, last four bits
    the status code"""
    _SUCCESS = 0b0000
    _NOT_PERFORMED = 0x1111

    CREATE_SUCCESS = FilestoreActionCode.CREATE_FILE_SNM << 4 | _SUCCESS
    CREATE_NOT_ALLOWED = FilestoreActionCode.CREATE_FILE_SNM << 4 | 0b0001
    CREATE_NOT_PERFORMED = FilestoreActionCode.CREATE_FILE_SNM << 4 | _NOT_PERFORMED

    DELETE_SUCCESS = FilestoreActionCode.DELETE_FILE_SNN << 4 | _SUCCESS
    DELETE_FILE_DOES_NOT_EXIST = FilestoreActionCode.DELETE_FILE_SNN << 4 | 0b0001
    DELETE_NOT_ALLOWED = FilestoreActionCode.DELETE_FILE_SNN << 4 | _NOT_PERFORMED

    RENAME_SUCCESS = FilestoreActionCode.RENAME_FILE_SNP << 4 | _SUCCESS
    RENAME_OLD_FILE_DOES_NOT_EXIST = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0001
    RENAME_NEW_FILE_DOES_EXIST = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0010
    RENAME_NOT_ALLOWED = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0011
    RENAME_NOT_PERFORMED = FilestoreActionCode.RENAME_FILE_SNP << 4 | _NOT_PERFORMED

    APPEND_SUCCESS = FilestoreActionCode.APPEND_FILE_SNP << 4 | _SUCCESS
    APPEND_FILE_NAME_ONE_NOT_EXISTS = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0001
    APPEND_FILE_NAME_TWO_NOT_EXISTS = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0010
    APPEND_NOT_ALLOWED = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0011
    APPEND_NOT_PERFORMED = FilestoreActionCode.APPEND_FILE_SNP << 4 | _NOT_PERFORMED

    REPLACE_SUCCESS = FilestoreActionCode.REPLACE_FILE_SNP << 4 | _SUCCESS
    REPLACE_FILE_NAME_ONE_DOES_NOT_EXIST = FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0001
    REPLACE_FILE_NAME_TWO_DOES_NOT_EXIST = FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0010
    REPLACE_NOT_ALLOWED = FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0011
    REPLACE_NOT_PERFORMED = FilestoreActionCode.REPLACE_FILE_SNP << 4 | _NOT_PERFORMED

    CREATE_DIR_SUCCESS = FilestoreActionCode.CREATE_DIR_SNN << 4 | _SUCCESS
    CREATE_DIR_CAN_NOT_BE_CREATED = FilestoreActionCode.CREATE_DIR_SNN << 4 | 0b0001
    CREATE_DIR_NOT_PERFORMED = FilestoreActionCode.CREATE_DIR_SNN << 4 | _NOT_PERFORMED

    REMOVE_DIR_SUCCESS = FilestoreActionCode.REMOVE_DIR_SNN << 4 | _SUCCESS
    REMOVE_DIR_DOES_NOT_EXIST = FilestoreActionCode.REMOVE_DIR_SNN << 4 | 0b0001
    REMOVE_DIR_NOT_ALLOWED = FilestoreActionCode.REMOVE_DIR_SNN << 4 | 0b0010
    REMOVE_DIR_NOT_PERFORMED = FilestoreActionCode.REMOVE_DIR_SNN << 4 | _NOT_PERFORMED

    DENY_FILE_DEL_SUCCESS = FilestoreActionCode.DENY_FILE_SMM << 4 | _SUCCESS
    DENY_FILE_DEL_NOT_ALLOWED = FilestoreActionCode.DENY_FILE_SMM << 4 | 0b0010
    DENY_FILE_DEL_NOT_PERFORMED = FilestoreActionCode.DENY_FILE_SMM << 4 | _NOT_PERFORMED

    DENY_DIR_DEL_SUCCESS = FilestoreActionCode.DENY_DIR_SNN << 4 | _SUCCESS
    DENY_DIR_DEL_NOT_ALLOWED = FilestoreActionCode.DENY_DIR_SNN << 4 | 0b0010
    DENY_DIR_DEL_NOT_PERFORMED = FilestoreActionCode.DENY_DIR_SNN << 4 | _NOT_PERFORMED
    INVALID = -1


def map_enum_status_code_to_int(status_code: FilestoreResponseStatusCode) -> int:
    return status_code & 0x0f


def map_enum_status_code_to_action_status_code(
        status_code: FilestoreResponseStatusCode
) -> Tuple[FilestoreActionCode, int]:
    """Map a given file store response status code to the action code and the corresponding
    4 bit status code. the status code will be 0x00 for a SUCCESS operation and 0b1111 if the
    operation was not performed"""
    try:
        status_code = FilestoreActionCode(status_code & 0xf0)
    except ValueError:
        # Invalid status code
        status_code = -1
    return status_code, status_code & 0x0f


def map_int_status_code_to_enum(
        action_code: FilestoreActionCode, status_code: int
) -> FilestoreResponseStatusCode:
    """Maps an action code and the status code of a filestore response to the status code.

    :param action_code:
    :param status_code:
    :return: The status code. Will be FilestoreResponseStatusCode.INVALID in case no valid status
        code was detected
    """
    try:
        status_code = FilestoreResponseStatusCode(action_code << 4 | status_code)
        return status_code
    except (IndexError, ValueError):
        return FilestoreResponseStatusCode.INVALID


class CfdpTlv:
    """Encapsulates the CFDP TLV (type-length-value) format.
    For more information, refer to CCSDS 727.0-B-5 p.77
    """
    MINIMAL_LEN = 2

    def __init__(
            self,
            tlv_type: TlvTypes,
            value: bytes
    ):
        """Constructor for TLV field.

        :param tlv_type:
        :param value:
        :raise ValueError: Length invalid or value length not equal to specified length
        """
        self.length = len(value)
        if self.length > 255:
            logger = get_console_logger()
            logger.warning('Length larger than allowed 255 bytes')
            raise ValueError
        self.tlv_type = tlv_type
        self.value = value

    def pack(self) -> bytearray:
        tlv_data = bytearray()
        tlv_data.append(self.tlv_type)
        tlv_data.append(self.length)
        tlv_data.extend(self.value)
        return tlv_data

    @classmethod
    def unpack(cls, raw_bytes: bytes) -> CfdpTlv:
        """Parses LV field at the start of the given bytearray

        :param raw_bytes:
        :raise ValueError: Invalid format of the raw bytearray or type field invalid
        :return:
        """
        if len(raw_bytes) < 2:
            logger = get_console_logger()
            logger.warning('Invalid length for TLV field, less than 2')
            raise ValueError
        try:
            tlv_type = TlvTypes(raw_bytes[0])
        except ValueError:
            logger = get_console_logger()
            logger.warning(
                f'TLV field invalid, found value {raw_bytes[0]} is not a possible TLV parameter'
            )
            raise ValueError

        value = bytearray()
        if len(raw_bytes) > 2:
            length = raw_bytes[1]
            if 2 + length > len(raw_bytes):
                logger = get_console_logger()
                logger.warning(f'Detected TLV length exceeds size of passed bytearray')
                raise ValueError
            value.extend(raw_bytes[2: 2 + length])
        return cls(
            tlv_type=tlv_type,
            value=value
        )

    @property
    def packet_len(self) -> int:
        return self.MINIMAL_LEN + len(self.value)


class EntityIdTlv:
    def __init__(self, entity_id: bytes):
        self.tlv = CfdpTlv(tlv_type=TlvTypes.ENTITY_ID, value=entity_id)

    @classmethod
    def __empty(cls) -> EntityIdTlv:
        return cls(
            entity_id=bytes()
        )

    def pack(self) -> bytes:
        return self.tlv.pack()

    @classmethod
    def unpack(cls, raw_bytes: bytes):
        entity_id_tlv = cls.__empty()
        entity_id_tlv.tlv = CfdpTlv.unpack(raw_bytes=raw_bytes)

    @property
    def packet_len(self):
        return self.tlv.packet_len


class FileStoreRequestBase:
    def __init__(
            self,
            action_code: FilestoreActionCode,
            first_file_name: str,
            second_file_name: str
    ):
        self.action_code = action_code
        self.first_file_name = first_file_name
        self.second_file_name = second_file_name

    def common_packer(self, status_code: int) -> bytearray:
        tlv_value = bytearray()
        tlv_value.append(self.action_code << 4 | status_code)
        first_name_lv = CfdpLv(
            value=self.first_file_name.encode()
        )
        tlv_value.extend(first_name_lv.pack())
        if self.action_code in [
            FilestoreActionCode.REPLACE_FILE_SNP, FilestoreActionCode.RENAME_FILE_SNP,
            FilestoreActionCode.APPEND_FILE_SNP
        ]:
            second_name_lv = CfdpLv(
                value=self.second_file_name.encode()
            )
            tlv_value.extend(second_name_lv.pack())
        return tlv_value

    @staticmethod
    def common_unpacker(
            raw_bytes: bytes, expected_tlv_type: TlvTypes
    ) -> Tuple[FilestoreActionCode, str, int, int, Optional[str]]:
        tlv = CfdpTlv.unpack(raw_bytes=raw_bytes)
        if tlv.tlv_type != expected_tlv_type:
            logger = get_console_logger()
            logger.warning('Invalid TLV type detected')
            raise ValueError
        current_idx = 0
        action_code_as_int = (tlv.value[current_idx] & 0xf0) >> 4
        try:
            action_code = FilestoreActionCode(action_code_as_int)
        except IndexError:
            logger = get_console_logger()
            logger.warning(
                f'Invalid action code in file store response with value {action_code_as_int}'
            )
            raise ValueError
        status_code_as_int = tlv.value[current_idx] & 0x0f
        current_idx += 1
        first_lv = CfdpLv.unpack(raw_bytes=raw_bytes[current_idx:])
        current_idx += first_lv.packet_len
        first_file_name = first_lv.value.decode()
        if action_code in [
            FilestoreActionCode.REPLACE_FILE_SNP, FilestoreActionCode.RENAME_FILE_SNP,
            FilestoreActionCode.APPEND_FILE_SNP
        ]:
            second_lv = CfdpLv.unpack(raw_bytes=tlv[current_idx:])
            current_idx += second_lv.packet_len
            second_file_name = second_lv.value.decode()
        else:
            second_file_name = None
        return action_code, first_file_name, status_code_as_int, current_idx, second_file_name


class FileStoreRequestTlv(FileStoreRequestBase):
    def __init__(
            self,
            action_code: FilestoreActionCode,
            first_file_name: str,
            second_file_name: str = ""
    ):
        super().__init__(
            action_code=action_code,
            first_file_name=first_file_name,
            second_file_name=second_file_name
        )
        self._build_tlv()

    @classmethod
    def __empty(cls) -> FileStoreRequestTlv:
        return cls(
            action_code=FilestoreActionCode.CREATE_FILE_SNM,
            first_file_name="",
            second_file_name=""
        )

    def _build_tlv(self):
        tlv_value = self.common_packer(status_code=0b0000)
        self.tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST,
            value=tlv_value
        )

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @classmethod
    def unpack(cls, raw_tlv: bytearray) -> FileStoreRequestTlv:
        filestore_req = cls.__empty()
        action_code, first_name, status_code, _, second_name = cls.common_unpacker(
            raw_bytes=raw_tlv, expected_tlv_type=TlvTypes.FILESTORE_REQUEST
        )
        filestore_req.action_code = action_code
        filestore_req.first_file_name = first_name
        if second_name is not None:
            filestore_req.second_file_name = second_name
        filestore_req._build_tlv()
        return filestore_req

    @property
    def packet_len(self):
        return self.tlv.packet_len


class FileStoreResponseTlv(FileStoreRequestBase):
    def __init__(
            self,
            action_code: FilestoreActionCode,
            status_code: FilestoreResponseStatusCode,
            first_file_name: str,
            second_file_name: str = "",
            filestore_msg: CfdpLv = CfdpLv(value=bytes())
    ):
        super().__init__(
            action_code=action_code,
            first_file_name=first_file_name,
            second_file_name=second_file_name
        )
        self.status_code = status_code
        self.filestore_msg = filestore_msg
        self._build_tlv()

    @classmethod
    def __empty(cls) -> FileStoreResponseTlv:
        return cls(
            action_code=FilestoreActionCode.CREATE_FILE_SNM,
            status_code=FilestoreResponseStatusCode.CREATE_SUCCESS,
            first_file_name="",
            second_file_name=""
        )

    def _build_tlv(self):
        status_code_as_int = map_enum_status_code_to_int(status_code=self.status_code)
        tlv_value = self.common_packer(status_code=status_code_as_int)
        tlv_value.extend(self.filestore_msg.pack())
        self.tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_RESPONSE,
            value=tlv_value
        )

    def pack(self) -> bytearray:
        return self.tlv.pack()

    @classmethod
    def unpack(cls, raw_tlv: bytearray) -> FileStoreResponseTlv:
        filestore_reply = cls.__empty()
        action_code, first_name, status_code, idx, second_name = cls.common_unpacker(
            raw_bytes=raw_tlv, expected_tlv_type=TlvTypes.FILESTORE_RESPONSE
        )
        filestore_reply.action_code = action_code
        filestore_reply.first_file_name = first_name
        try:
            status_code_named = FilestoreResponseStatusCode(action_code << 4 | status_code)
        except ValueError:
            logger = get_console_logger()
            logger.warning(
                f'Invalid status code in file store response with value {status_code} for '
                f'action code {action_code}'
            )
            raise ValueError
        filestore_reply.status_code = status_code_named
        if second_name is not None:
            filestore_reply.second_file_name = second_name
        filestore_reply.filestore_msg = CfdpLv(value=raw_tlv[idx:])
        filestore_reply._build_tlv()
        return filestore_reply

    @property
    def packet_len(self):
        return self.tlv.packet_len
