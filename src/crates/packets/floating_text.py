import struct


class BinaryWriter:
    def __init__(self):
        self.data = bytearray()

    def write_byte(self, value: int):
        self.data.extend(struct.pack("<b", value))

    def write_float(self, value: float):
        self.data.extend(struct.pack("<f", value))

    def write_signed_short(self, value: int):
        self.data.extend(struct.pack("<h", value))

    def write_signed_int(self, value: int):
        self.data.extend(struct.pack("<i", value))

    def write_unsigned_int64(self, value: int):
        self.data.extend(struct.pack("<Q", value))

    def write_signed_int64(self, value: int):
        self.data.extend(struct.pack("<q", value))

    def write_signed_big_endian_int(self, value: int):
        self.data.extend(struct.pack(">i", value))

    def write_unsigned_varint64(self, value: int):
        value = int(value)
        while value >= 0x80:
            self.data.append((value & 0x7F) | 0x80)
            value >>= 7
        self.data.append(value)

    def write_varint64(self, value: int):
        self.write_unsigned_varint64(value & 0xFFFFFFFFFFFFFFFF)

    def write_string(self, value: str):
        encoded = value.encode("utf-8")
        self.write_unsigned_varint64(len(encoded))
        self.data.extend(encoded)

    def bytes(self) -> bytes:
        return bytes(self.data)


class FloatingTextPacket:
    ADD_ACTOR_PACKET_ID = 13
    REMOVE_ACTOR_PACKET_ID = 14

    @staticmethod
    def add(
        actor_id: int,
        text: str,
        x: float,
        y: float,
        z: float,
        actor_identifier: str = "armor_stand",
    ) -> bytes:
        writer = BinaryWriter()
        writer.write_varint64(actor_id)
        writer.write_unsigned_varint64(actor_id)
        writer.write_string(actor_identifier)
        writer.write_float(x)
        writer.write_float(y)
        writer.write_float(z)
        writer.write_unsigned_int64(0)
        writer.write_signed_int64(0)
        writer.write_unsigned_int64(0)
        writer.write_signed_int(0)
        writer.write_signed_big_endian_int(590852)
        writer.write_string(text)
        writer.write_unsigned_int64(22799473113563942)
        writer.write_signed_int64(6491382630230130945)
        writer.write_unsigned_int64(144442844453603100)
        writer.write_signed_int64(147508270825868034)
        writer.write_unsigned_int64(53750529787)
        return writer.bytes()

    @staticmethod
    def remove(actor_id: int) -> bytes:
        writer = BinaryWriter()
        writer.write_varint64(actor_id)
        return writer.bytes()
