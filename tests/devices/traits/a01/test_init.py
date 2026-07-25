import datetime
import json
from typing import Any

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockMessageProtocol, RoborockZeoProtocol
from tests.fixtures.channel_fixtures import FakeChannel
from tests.protocols.common import build_a01_message


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="dyad_api")
def dyad_api_fixture(fake_channel: FakeChannel) -> DyadApi:
    return DyadApi(fake_channel)  # type: ignore[arg-type]


@pytest.fixture(name="zeo_api")
def zeo_api_fixture(fake_channel: FakeChannel) -> ZeoApi:
    return ZeoApi(fake_channel)  # type: ignore[arg-type]


async def test_dyad_api_query_values(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Test that DyadApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(
        build_a01_message(
            {
                209: 1,  # POWER
                201: 6,  # STATUS
                207: 3,  # WATER_LEVEL
                214: 120,  # MESH_LEFT
                215: 90,  # BRUSH_LEFT
                227: 85,  # SILENT_MODE_START_TIME
                229: "3,4,5",  # RECENT_RUN_TIME
                230: 123456,  # TOTAL_RUN_TIME
                222: 1,  # STAND_LOCK_AUTO_RUN
                224: 0,  # AUTO_DRY_MODE
            }
        )
    )
    result = await dyad_api.query_values(
        [
            RoborockDyadDataProtocol.POWER,
            RoborockDyadDataProtocol.STATUS,
            RoborockDyadDataProtocol.WATER_LEVEL,
            RoborockDyadDataProtocol.MESH_LEFT,
            RoborockDyadDataProtocol.BRUSH_LEFT,
            RoborockDyadDataProtocol.SILENT_MODE_START_TIME,
            RoborockDyadDataProtocol.RECENT_RUN_TIME,
            RoborockDyadDataProtocol.TOTAL_RUN_TIME,
            RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN,
            RoborockDyadDataProtocol.AUTO_DRY_MODE,
        ]
    )
    assert result == {
        RoborockDyadDataProtocol.POWER: 1,
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.WATER_LEVEL: "l3",
        RoborockDyadDataProtocol.MESH_LEFT: 352800,
        RoborockDyadDataProtocol.BRUSH_LEFT: 354600,
        RoborockDyadDataProtocol.SILENT_MODE_START_TIME: datetime.time(1, 25),
        RoborockDyadDataProtocol.RECENT_RUN_TIME: [3, 4, 5],
        RoborockDyadDataProtocol.TOTAL_RUN_TIME: 123456,
        RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: True,
        RoborockDyadDataProtocol.AUTO_DRY_MODE: False,
    }

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"] == {"10000": "[209, 201, 207, 214, 215, 227, 229, 230, 222, 224]"}
    assert "t" in payload_data


@pytest.mark.parametrize(
    ("query", "response", "expected_result"),
    [
        (
            [RoborockDyadDataProtocol.STATUS],
            {
                7: 1,
                RoborockDyadDataProtocol.STATUS: 3,
                9999: -3,
            },
            {
                RoborockDyadDataProtocol.STATUS: "charging",
            },
        ),
        (
            [RoborockDyadDataProtocol.SILENT_MODE_START_TIME],
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: "invalid",
            },
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: None,
            },
        ),
        (
            [RoborockDyadDataProtocol.SILENT_MODE_START_TIME],
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: 85,
                RoborockDyadDataProtocol.POWER: 2,
                9999: -3,
            },
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: datetime.time(1, 25),
            },
        ),
    ],
    ids=[
        "ignored-unknown-protocol",
        "invalid-value",
        "additional-returned-values",
    ],
)
async def test_dyad_invalid_response_value(
    query: list[RoborockDyadDataProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockDyadDataProtocol, Any],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """Test that DyadApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(build_a01_message(response))

    result = await dyad_api.query_values(query)
    assert result == expected_result


async def test_dyad_api_query_wetdryvac_values(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Newer wet/dry vac dps (e.g. F25) decode instead of colliding on DRYING_STATUS."""
    fake_channel.response_queue.append(
        build_a01_message(
            {
                243: 2,  # DOCK_TYPE
                247: 100,  # DRYING_RATE
                238: 2,  # SET_CLEANSER_AMOUNT
                242: 3,  # SELF_CLEAN_WATER_TEMP_LEVEL_SET
                241: 1,  # CLEAN_ASSIST_POWER_SET
                244: 3,  # WATER_MODE_SUCTION
                245: 2,  # WATER_MODE_BRUSH_SPEED
                240: 1,  # LIGHT_SET
                239: 1,  # AUTO_SMART_SELF_CLEAN_SET
                248: 0,  # FLAT_STATUS
            }
        )
    )
    result = await dyad_api.query_values(
        [
            RoborockDyadDataProtocol.DOCK_TYPE,
            RoborockDyadDataProtocol.DRYING_RATE,
            RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT,
            RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET,
            RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET,
            RoborockDyadDataProtocol.WATER_MODE_SUCTION,
            RoborockDyadDataProtocol.WATER_MODE_BRUSH_SPEED,
            RoborockDyadDataProtocol.LIGHT_SET,
            RoborockDyadDataProtocol.AUTO_SMART_SELF_CLEAN_SET,
            RoborockDyadDataProtocol.FLAT_STATUS,
        ]
    )
    assert result == {
        RoborockDyadDataProtocol.DOCK_TYPE: "turbo",
        RoborockDyadDataProtocol.DRYING_RATE: 100,
        RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT: "normal",
        RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET: "high",
        RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET: "low",
        RoborockDyadDataProtocol.WATER_MODE_SUCTION: "l3",
        RoborockDyadDataProtocol.WATER_MODE_BRUSH_SPEED: "l2",
        RoborockDyadDataProtocol.LIGHT_SET: True,
        RoborockDyadDataProtocol.AUTO_SMART_SELF_CLEAN_SET: True,
        RoborockDyadDataProtocol.FLAT_STATUS: False,
    }


async def test_dyad_out_of_range_enum_is_unknown(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Out-of-range enum values decode to 'unknown' rather than a plausible-but-wrong label."""
    fake_channel.response_queue.append(
        build_a01_message(
            {
                206: 7,  # SUCTION
                207: 9,  # WATER_LEVEL
                216: 99999,  # ERROR
                243: 5,  # DOCK_TYPE
                242: 9,  # SELF_CLEAN_WATER_TEMP_LEVEL_SET
                241: 9,  # CLEAN_ASSIST_POWER_SET
            }
        )
    )
    result = await dyad_api.query_values(
        [
            RoborockDyadDataProtocol.SUCTION,
            RoborockDyadDataProtocol.WATER_LEVEL,
            RoborockDyadDataProtocol.ERROR,
            RoborockDyadDataProtocol.DOCK_TYPE,
            RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET,
            RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET,
        ]
    )
    assert result == {
        RoborockDyadDataProtocol.SUCTION: "unknown",
        RoborockDyadDataProtocol.WATER_LEVEL: "unknown",
        RoborockDyadDataProtocol.ERROR: "unknown",
        RoborockDyadDataProtocol.DOCK_TYPE: "unknown",
        RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET: "unknown",
        RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET: "unknown",
    }


async def test_zeo_api_query_values(zeo_api: ZeoApi, fake_channel: FakeChannel):
    """Test that ZeoApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(
        build_a01_message(
            {
                203: 6,  # spinning
                207: 3,  # medium
                226: 1,
                227: 0,
                224: 1,  # Times after clean. Testing int value
                218: 0,  # Washing left. Testing zero int value
            }
        )
    )
    result = await zeo_api.query_values(
        [
            RoborockZeoProtocol.STATE,
            RoborockZeoProtocol.TEMP,
            RoborockZeoProtocol.DETERGENT_EMPTY,
            RoborockZeoProtocol.SOFTENER_EMPTY,
            RoborockZeoProtocol.TIMES_AFTER_CLEAN,
            RoborockZeoProtocol.WASHING_LEFT,
        ]
    )
    assert result == {
        # Note: Bug here, should return enum/bool values
        RoborockZeoProtocol.STATE: "spinning",
        RoborockZeoProtocol.TEMP: "medium",
        RoborockZeoProtocol.DETERGENT_EMPTY: True,
        RoborockZeoProtocol.SOFTENER_EMPTY: False,
        RoborockZeoProtocol.TIMES_AFTER_CLEAN: 1,
        RoborockZeoProtocol.WASHING_LEFT: 0,
    }

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"] == {"10000": "[203, 207, 226, 227, 224, 218]"}
    assert "t" in payload_data


@pytest.mark.parametrize(
    ("query", "response", "expected_result"),
    [
        (
            [RoborockZeoProtocol.STATE],
            {
                7: 1,
                RoborockZeoProtocol.STATE: 1,
                9999: -3,
            },
            {
                RoborockZeoProtocol.STATE: "standby",
            },
        ),
        (
            [RoborockZeoProtocol.WASHING_LEFT],
            {
                RoborockZeoProtocol.WASHING_LEFT: "invalid",
            },
            {
                RoborockZeoProtocol.WASHING_LEFT: None,
            },
        ),
        (
            [RoborockZeoProtocol.STATE],
            {
                RoborockZeoProtocol.STATE: 1,
                RoborockZeoProtocol.WASHING_LEFT: 2,
                9999: -3,
            },
            {
                RoborockZeoProtocol.STATE: "standby",
            },
        ),
    ],
    ids=[
        "ignored-unknown-protocol",
        "invalid-value",
        "additional-returned-values",
    ],
)
async def test_zeo_invalid_response_value(
    query: list[RoborockZeoProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockZeoProtocol, Any],
    zeo_api: ZeoApi,
    fake_channel: FakeChannel,
):
    """Test that ZeoApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(build_a01_message(response))

    result = await zeo_api.query_values(query)
    assert result == expected_result


async def test_dyad_api_set_value(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Test DyadApi set_value sends correct command."""
    await dyad_api.set_value(RoborockDyadDataProtocol.POWER, 1)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]

    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"

    # decode the payload to verify contents
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    # A01 protocol expects values to be strings in the dps dict
    assert payload_data["dps"] == {"209": 1}
    assert "t" in payload_data


async def test_zeo_api_set_value(zeo_api: ZeoApi, fake_channel: FakeChannel):
    """Test ZeoApi set_value sends correct command."""
    await zeo_api.set_value(RoborockZeoProtocol.MODE, "standard")

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]

    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"

    # decode the payload to verify contents
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    # A01 protocol expects values to be strings in the dps dict
    assert payload_data["dps"] == {"204": "standard"}
    assert "t" in payload_data
