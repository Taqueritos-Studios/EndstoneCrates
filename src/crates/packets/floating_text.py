import struct


class BinaryWriter:
    def __init__(self):
        self.data = bytearray()

    def write_signed_byte(self, value: int):
        self.data.extend(struct.pack("<b", value))

    def write_unsigned_byte(self, value: int):
        self.data.extend(struct.pack("<B", value))

    def write_float(self, value: float):
        self.data.extend(struct.pack("<f", value))

    def write_unsigned_varint(self, value: int):
        value = int(value)
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError("unsigned varint is outside the uint32 range")
        self._write_unsigned_varint(value)

    def write_unsigned_varint64(self, value: int):
        value = int(value)
        if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
            raise ValueError("unsigned varint64 is outside the uint64 range")
        self._write_unsigned_varint(value)

    def _write_unsigned_varint(self, value: int):
        while value >= 0x80:
            self.data.append((value & 0x7F) | 0x80)
            value >>= 7
        self.data.append(value)

    def write_varint64(self, value: int):
        value = int(value)
        if value < -(1 << 63) or value >= (1 << 63):
            raise ValueError("varint64 is outside the int64 range")
        encoded = (value << 1) ^ (value >> 63)
        self.write_unsigned_varint64(encoded)

    def write_varint(self, value: int):
        value = int(value)
        if value < -(1 << 31) or value >= (1 << 31):
            raise ValueError("varint is outside the int32 range")
        encoded = (value << 1) ^ (value >> 31)
        self.write_unsigned_varint(encoded)

    def write_string(self, value: str):
        encoded = value.encode("utf-8")
        self.write_unsigned_varint(len(encoded))
        self.data.extend(encoded)

    def bytes(self) -> bytes:
        return bytes(self.data)


class FloatingTextPacket:
    ADD_ACTOR_PACKET_ID = 13
    REMOVE_ACTOR_PACKET_ID = 14
    SUPPORTED_PROTOCOLS = frozenset({2168})

    DATA_TYPE_BYTE = 0
    DATA_TYPE_INT = 2
    DATA_TYPE_FLOAT = 3
    DATA_TYPE_STRING = 4
    DATA_TYPE_INT64 = 7

    ACTOR_DATA_FLAGS = 0
    ACTOR_DATA_VARIANT = 2
    ACTOR_DATA_NAME = 4
    ACTOR_DATA_SCALE = 38
    ACTOR_DATA_BOUNDING_BOX_WIDTH = 53
    ACTOR_DATA_BOUNDING_BOX_HEIGHT = 54
    ACTOR_DATA_NAMETAG_ALWAYS_SHOW = 81

    FLAG_NO_AI = 16

    @classmethod
    def supports(cls, protocol_version: int) -> bool:
        return protocol_version in cls.SUPPORTED_PROTOCOLS

    @classmethod
    def require_supported(cls, protocol_version: int):
        if not cls.supports(protocol_version):
            supported = ", ".join(str(version) for version in sorted(cls.SUPPORTED_PROTOCOLS))
            raise ValueError(
                f"unsupported Bedrock protocol {protocol_version}; supported protocol: {supported}"
            )

    @staticmethod
    def normalize_actor_identifier(actor_identifier: str) -> str:
        value = str(actor_identifier).strip().lower()
        if not value:
            return "minecraft:falling_block"
        value = value if ":" in value else f"minecraft:{value}"
        # Older configs used armor_stand, whose invisibility also hides its
        # name tag on Bedrock. Migrate it to the air-block text carrier.
        if value == "minecraft:armor_stand":
            return "minecraft:falling_block"
        return value

    @staticmethod
    def write_actor_data_header(writer: BinaryWriter, data_id: int, data_type: int):
        # Protocol 2168 uses a tagged variant for actor metadata: ID, a
        # VarUInt discriminator, the selected payload's uint8 Type, then Value.
        writer.write_unsigned_varint(data_id)
        writer.write_unsigned_varint(data_type)
        writer.write_unsigned_byte(data_type)

    @classmethod
    def add(
        cls,
        actor_id: int,
        text: str,
        x: float,
        y: float,
        z: float,
        actor_identifier: str = "falling_block",
        *,
        protocol_version: int = 2168,
    ) -> bytes:
        cls.require_supported(protocol_version)

        writer = BinaryWriter()
        writer.write_varint64(actor_id)
        writer.write_unsigned_varint64(actor_id)
        writer.write_string(cls.normalize_actor_identifier(actor_identifier))

        for value in (x, y, z):
            writer.write_float(value)
        for _ in range(7):
            writer.write_float(0.0)

        # Attributes
        writer.write_unsigned_varint(0)

        # Synched actor data
        writer.write_unsigned_varint(7)

        flags = 1 << cls.FLAG_NO_AI
        cls.write_actor_data_header(writer, cls.ACTOR_DATA_FLAGS, cls.DATA_TYPE_INT64)
        writer.write_varint64(flags)

        cls.write_actor_data_header(writer, cls.ACTOR_DATA_SCALE, cls.DATA_TYPE_FLOAT)
        writer.write_float(0.01)

        cls.write_actor_data_header(
            writer,
            cls.ACTOR_DATA_BOUNDING_BOX_WIDTH,
            cls.DATA_TYPE_FLOAT,
        )
        writer.write_float(0.0)

        cls.write_actor_data_header(
            writer,
            cls.ACTOR_DATA_BOUNDING_BOX_HEIGHT,
            cls.DATA_TYPE_FLOAT,
        )
        writer.write_float(0.0)

        cls.write_actor_data_header(writer, cls.ACTOR_DATA_NAME, cls.DATA_TYPE_STRING)
        writer.write_string(str(text))

        # Falling-block variant 0 is air, so there is no visible carrier model.
        cls.write_actor_data_header(writer, cls.ACTOR_DATA_VARIANT, cls.DATA_TYPE_INT)
        writer.write_varint(0)

        cls.write_actor_data_header(
            writer,
            cls.ACTOR_DATA_NAMETAG_ALWAYS_SHOW,
            cls.DATA_TYPE_BYTE,
        )
        writer.write_signed_byte(1)

        # Empty integer properties, float properties, and actor links.
        writer.write_unsigned_varint(0)
        writer.write_unsigned_varint(0)
        writer.write_unsigned_varint(0)
        return writer.bytes()

    @classmethod
    def remove(cls, actor_id: int, *, protocol_version: int = 2168) -> bytes:
        cls.require_supported(protocol_version)
        writer = BinaryWriter()
        writer.write_varint64(actor_id)
        return writer.bytes()
