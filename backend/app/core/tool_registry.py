"""
Claude 工具注册表
AI 原生设计：Claude 通过工具调用外部能力，而非硬编码逻辑
所有工具的 JSON Schema 定义在此集中管理
"""

# ─── 情感陪伴工具 ────────────────────────────────────────────────────────────

TOOL_SAVE_MEMORY = {
    "name": "save_user_memory",
    "description": "将用户提到的重要个人信息保存到记忆库，包括姓名、家庭成员、爱好、健康状况、重要日期等",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["personal", "family", "health", "hobby", "important_date", "preference"],
                "description": "记忆类别"
            },
            "key": {
                "type": "string",
                "description": "记忆的键名，如 'name', 'daughter_name', 'blood_pressure_medication'"
            },
            "value": {
                "type": "string",
                "description": "记忆的内容"
            },
            "note": {
                "type": "string",
                "description": "额外备注，可选"
            }
        },
        "required": ["category", "key", "value"]
    }
}

TOOL_GET_MEMORY = {
    "name": "get_user_memory",
    "description": "查询用户的记忆信息，在需要个性化回复时调用",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["personal", "family", "health", "hobby", "important_date", "preference", "all"],
                "description": "查询的记忆类别，'all' 表示查询所有"
            }
        },
        "required": ["category"]
    }
}

TOOL_LOG_MOOD = {
    "name": "log_mood",
    "description": "记录用户当前的情绪状态，用于情绪趋势分析和心理关怀触发",
    "input_schema": {
        "type": "object",
        "properties": {
            "mood": {
                "type": "string",
                "enum": ["very_happy", "happy", "neutral", "sad", "very_sad", "anxious", "angry"],
                "description": "检测到的情绪状态"
            },
            "trigger": {
                "type": "string",
                "description": "触发该情绪的事件或原因，可选"
            }
        },
        "required": ["mood"]
    }
}

# ─── 健康医疗工具 ────────────────────────────────────────────────────────────

TOOL_CHECK_DRUG_INTERACTION = {
    "name": "check_drug_interaction",
    "description": "检查多种药物之间是否存在相互作用或禁忌，保障用药安全",
    "input_schema": {
        "type": "object",
        "properties": {
            "drugs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "药物名称列表，至少两种"
            }
        },
        "required": ["drugs"]
    }
}

TOOL_TRIGGER_SOS = {
    "name": "trigger_sos",
    "description": "触发紧急SOS求救，向绑定的紧急联系人发送位置和求救通知",
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "用户ID"
            },
            "emergency_type": {
                "type": "string",
                "enum": ["fall", "chest_pain", "stroke", "other"],
                "description": "紧急情况类型"
            },
            "message": {
                "type": "string",
                "description": "附加说明"
            }
        },
        "required": ["user_id", "emergency_type"]
    }
}

TOOL_SET_MEDICATION_REMINDER = {
    "name": "set_medication_reminder",
    "description": "为用户设置用药提醒，支持每日多次",
    "input_schema": {
        "type": "object",
        "properties": {
            "drug_name": {
                "type": "string",
                "description": "药物名称"
            },
            "times": {
                "type": "array",
                "items": {"type": "string"},
                "description": "每日服药时间，格式 HH:MM，如 ['08:00', '20:00']"
            },
            "dosage": {
                "type": "string",
                "description": "每次剂量，如 '1片'"
            },
            "notes": {
                "type": "string",
                "description": "服药注意事项，可选"
            }
        },
        "required": ["drug_name", "times", "dosage"]
    }
}

TOOL_GET_HEALTH_RECORDS = {
    "name": "get_health_records",
    "description": "获取用户的健康档案，包括慢病信息、过敏史、用药记录等",
    "input_schema": {
        "type": "object",
        "properties": {
            "record_type": {
                "type": "string",
                "enum": ["chronic_disease", "allergy", "medication", "vitals", "all"],
                "description": "健康档案类型"
            }
        },
        "required": ["record_type"]
    }
}

# ─── 安全防护工具 ────────────────────────────────────────────────────────────

TOOL_REPORT_FRAUD = {
    "name": "report_fraud_attempt",
    "description": "记录并上报诈骗事件，供平台反诈数据库更新",
    "input_schema": {
        "type": "object",
        "properties": {
            "fraud_type": {
                "type": "string",
                "enum": ["phone_scam", "online_scam", "health_product_fraud", "romance_scam", "impersonation"],
                "description": "诈骗类型"
            },
            "description": {
                "type": "string",
                "description": "诈骗事件描述"
            },
            "evidence": {
                "type": "string",
                "description": "证据信息（电话号码、截图描述等），可选"
            }
        },
        "required": ["fraud_type", "description"]
    }
}

# ─── 工具集合（按模块分组）────────────────────────────────────────────────────

COMPANION_TOOLS = [TOOL_SAVE_MEMORY, TOOL_GET_MEMORY, TOOL_LOG_MOOD]

HEALTH_TOOLS = [
    TOOL_CHECK_DRUG_INTERACTION,
    TOOL_TRIGGER_SOS,
    TOOL_SET_MEDICATION_REMINDER,
    TOOL_GET_HEALTH_RECORDS,
]

SAFETY_TOOLS = [TOOL_REPORT_FRAUD]
