"""
工具注册表结构验证
确保所有工具 Schema 符合 Claude API 要求
"""
import pytest
from app.core.tool_registry import (
    COMPANION_TOOLS, HEALTH_TOOLS, SAFETY_TOOLS,
    TOOL_SAVE_MEMORY, TOOL_GET_MEMORY, TOOL_LOG_MOOD,
    TOOL_CHECK_DRUG_INTERACTION, TOOL_TRIGGER_SOS,
    TOOL_SET_MEDICATION_REMINDER, TOOL_REPORT_FRAUD,
)

ALL_TOOLS = COMPANION_TOOLS + HEALTH_TOOLS + SAFETY_TOOLS


def test_all_tools_have_required_fields():
    for tool in ALL_TOOLS:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool '{tool['name']}' missing 'description'"
        assert "input_schema" in tool, f"Tool '{tool['name']}' missing 'input_schema'"


def test_all_schemas_are_objects():
    for tool in ALL_TOOLS:
        schema = tool["input_schema"]
        assert schema["type"] == "object", f"Tool '{tool['name']}' schema must be type 'object'"
        assert "properties" in schema


def test_required_fields_are_lists():
    for tool in ALL_TOOLS:
        schema = tool["input_schema"]
        if "required" in schema:
            assert isinstance(schema["required"], list)


def test_tool_names_unique():
    names = [t["name"] for t in ALL_TOOLS]
    assert len(names) == len(set(names)), "Duplicate tool names found"


def test_companion_tools_count():
    assert len(COMPANION_TOOLS) == 3


def test_health_tools_count():
    assert len(HEALTH_TOOLS) == 4


def test_mood_enum_values():
    mood_enum = TOOL_LOG_MOOD["input_schema"]["properties"]["mood"]["enum"]
    assert "happy" in mood_enum
    assert "sad" in mood_enum
    assert "very_sad" in mood_enum


def test_drug_interaction_requires_drugs():
    required = TOOL_CHECK_DRUG_INTERACTION["input_schema"]["required"]
    assert "drugs" in required


def test_sos_required_fields():
    required = TOOL_TRIGGER_SOS["input_schema"]["required"]
    assert "user_id" in required
    assert "emergency_type" in required


def test_emergency_type_enum():
    enum = TOOL_TRIGGER_SOS["input_schema"]["properties"]["emergency_type"]["enum"]
    assert "fall" in enum
    assert "chest_pain" in enum
    assert "stroke" in enum


def test_save_memory_categories():
    enum = TOOL_SAVE_MEMORY["input_schema"]["properties"]["category"]["enum"]
    expected = {"personal", "family", "health", "hobby", "important_date", "preference"}
    assert expected.issubset(set(enum))


def test_fraud_type_enum():
    enum = TOOL_REPORT_FRAUD["input_schema"]["properties"]["fraud_type"]["enum"]
    assert "phone_scam" in enum
    assert "romance_scam" in enum
