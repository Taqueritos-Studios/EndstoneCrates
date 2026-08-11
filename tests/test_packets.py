import importlib.util
import struct
import unittest
from pathlib import Path


PACKET_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "crates" / "packets" / "floating_text.py"
)
SPEC = importlib.util.spec_from_file_location("floating_text", PACKET_MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PACKET_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKET_MODULE)
BinaryWriter = PACKET_MODULE.BinaryWriter
FloatingTextPacket = PACKET_MODULE.FloatingTextPacket


class BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read(self, size: int) -> bytes:
        result = self.data[self.offset : self.offset + size]
        if len(result) != size:
            raise AssertionError("packet ended unexpectedly")
        self.offset += size
        return result

    def read_unsigned_byte(self) -> int:
        return struct.unpack("<B", self.read(1))[0]

    def read_signed_byte(self) -> int:
        return struct.unpack("<b", self.read(1))[0]

    def read_float(self) -> float:
        return struct.unpack("<f", self.read(4))[0]

    def read_unsigned_varint(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.read_unsigned_byte()
            result |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                return result
            shift += 7
            if shift >= 70:
                raise AssertionError("invalid varint")

    def read_varint64(self) -> int:
        value = self.read_unsigned_varint()
        return (value >> 1) ^ -(value & 1)

    def read_string(self) -> str:
        return self.read(self.read_unsigned_varint()).decode("utf-8")


class FloatingTextPacketTests(unittest.TestCase):
    def test_signed_actor_ids_use_zigzag_varints(self):
        writer = BinaryWriter()
        writer.write_varint64(1)
        self.assertEqual(writer.bytes(), b"\x02")

        writer = BinaryWriter()
        writer.write_varint64(-1)
        self.assertEqual(writer.bytes(), b"\x01")

    def test_add_actor_matches_protocol_2168_layout(self):
        actor_id = 42_000_001
        text = "§6Vote Crate\n§eUse a Vote Key"
        packet = FloatingTextPacket.add(
            actor_id,
            text,
            10.5,
            65.35,
            -2.5,
            "armor_stand",
            protocol_version=2168,
        )
        reader = BinaryReader(packet)

        self.assertEqual(reader.read_varint64(), actor_id)
        self.assertEqual(reader.read_unsigned_varint(), actor_id)
        self.assertEqual(reader.read_string(), "minecraft:falling_block")
        self.assertAlmostEqual(reader.read_float(), 10.5)
        self.assertAlmostEqual(reader.read_float(), 65.35, places=4)
        self.assertAlmostEqual(reader.read_float(), -2.5)
        self.assertEqual([reader.read_float() for _ in range(7)], [0.0] * 7)

        self.assertEqual(reader.read_unsigned_varint(), 0)  # attributes
        self.assertEqual(reader.read_unsigned_varint(), 7)  # actor data entries

        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.ACTOR_DATA_FLAGS)
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_INT64)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_INT64)
        expected_flags = 1 << FloatingTextPacket.FLAG_NO_AI
        self.assertEqual(reader.read_varint64(), expected_flags)

        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.ACTOR_DATA_SCALE)
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_FLOAT)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_FLOAT)
        self.assertAlmostEqual(reader.read_float(), 0.01)

        self.assertEqual(
            reader.read_unsigned_varint(),
            FloatingTextPacket.ACTOR_DATA_BOUNDING_BOX_WIDTH,
        )
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_FLOAT)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_FLOAT)
        self.assertEqual(reader.read_float(), 0.0)

        self.assertEqual(
            reader.read_unsigned_varint(),
            FloatingTextPacket.ACTOR_DATA_BOUNDING_BOX_HEIGHT,
        )
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_FLOAT)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_FLOAT)
        self.assertEqual(reader.read_float(), 0.0)

        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.ACTOR_DATA_NAME)
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_STRING)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_STRING)
        self.assertEqual(reader.read_string(), text)

        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.ACTOR_DATA_VARIANT)
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_INT)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_INT)
        self.assertEqual(reader.read_varint64(), 0)

        self.assertEqual(
            reader.read_unsigned_varint(),
            FloatingTextPacket.ACTOR_DATA_NAMETAG_ALWAYS_SHOW,
        )
        self.assertEqual(reader.read_unsigned_varint(), FloatingTextPacket.DATA_TYPE_BYTE)
        self.assertEqual(reader.read_unsigned_byte(), FloatingTextPacket.DATA_TYPE_BYTE)
        self.assertEqual(reader.read_signed_byte(), 1)

        self.assertEqual(reader.read_unsigned_varint(), 0)  # integer properties
        self.assertEqual(reader.read_unsigned_varint(), 0)  # float properties
        self.assertEqual(reader.read_unsigned_varint(), 0)  # actor links
        self.assertEqual(reader.offset, len(packet))

    def test_remove_actor_uses_signed_zigzag_id(self):
        self.assertEqual(
            FloatingTextPacket.remove(1, protocol_version=2168),
            b"\x02",
        )

    def test_unsupported_protocol_is_rejected_before_sending(self):
        self.assertFalse(FloatingTextPacket.supports(2167))
        with self.assertRaisesRegex(ValueError, "unsupported Bedrock protocol 2167"):
            FloatingTextPacket.add(1, "test", 0, 0, 0, protocol_version=2167)


if __name__ == "__main__":
    unittest.main()
