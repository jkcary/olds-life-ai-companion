"""
健康模块工具实现
真实场景中对接医疗数据库和第三方服务，此处为演示实现
"""
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


# 常见药物禁忌数据库（演示数据，真实场景需对接医药数据库）
DRUG_INTERACTIONS_DB: dict[frozenset, dict] = {
    frozenset(["阿司匹林", "华法林"]): {
        "severity": "high",
        "description": "两药合用显著增加出血风险，禁止同时使用",
        "recommendation": "如需同时使用，必须在医生指导下严密监测凝血功能",
    },
    frozenset(["布洛芬", "阿司匹林"]): {
        "severity": "medium",
        "description": "NSAIDs合用增加胃肠道出血风险，降低阿司匹林的抗血小板效果",
        "recommendation": "避免同时使用，可选择对乙酰氨基酚替代布洛芬",
    },
    frozenset(["二甲双胍", "碘造影剂"]): {
        "severity": "high",
        "description": "碘造影剂可影响肾功能，导致二甲双胍蓄积引起乳酸酸中毒",
        "recommendation": "做增强CT前48小时停用二甲双胍，检查后48小时后复用",
    },
}


async def check_drug_interaction(drugs: list[str]) -> dict:
    """检查药物相互作用"""
    if len(drugs) < 2:
        return {"interactions": [], "message": "需要至少两种药物才能检查配伍禁忌"}

    interactions = []
    drug_set = set(drugs)

    for pair, info in DRUG_INTERACTIONS_DB.items():
        if pair.issubset(drug_set):
            drug_names = list(pair)
            interactions.append({
                "drugs": drug_names,
                "severity": info["severity"],
                "description": info["description"],
                "recommendation": info["recommendation"],
            })

    return {
        "drugs_checked": drugs,
        "interactions_found": len(interactions),
        "interactions": interactions,
        "safe": len(interactions) == 0,
    }


async def trigger_sos(
    db: AsyncSession,
    user_id: str,
    emergency_type: str,
    message: str = "",
) -> dict:
    """触发 SOS 急救"""
    # 获取紧急联系人
    result = await db.execute(
        text("SELECT name, phone FROM emergency_contacts WHERE user_id = :uid ORDER BY priority"),
        {"uid": user_id},
    )
    contacts = result.fetchall()

    # 记录 SOS 事件
    await db.execute(
        text("""
            INSERT INTO sos_events (user_id, emergency_type, message, triggered_at, status)
            VALUES (:user_id, :emergency_type, :message, :triggered_at, 'triggered')
        """),
        {
            "user_id": user_id,
            "emergency_type": emergency_type,
            "message": message,
            "triggered_at": datetime.now(UTC).isoformat(),
        },
    )
    await db.commit()

    notified = [{"name": c[0], "phone": c[1]} for c in contacts]

    # 真实场景：此处调用短信/推送服务通知联系人
    return {
        "sos_triggered": True,
        "emergency_type": emergency_type,
        "contacts_notified": notified,
        "message": "已向紧急联系人发送求救通知，请立即拨打120！",
        "emergency_number": "120",
    }


async def set_medication_reminder(
    db: AsyncSession,
    user_id: str,
    drug_name: str,
    times: list[str],
    dosage: str,
    notes: str | None = None,
) -> dict:
    """设置用药提醒"""
    # 先删除该药物的旧提醒
    await db.execute(
        text("DELETE FROM medication_reminders WHERE user_id = :uid AND drug_name = :drug"),
        {"uid": user_id, "drug": drug_name},
    )

    for t in times:
        await db.execute(
            text("""
                INSERT INTO medication_reminders (user_id, drug_name, reminder_time, dosage, notes)
                VALUES (:user_id, :drug_name, :reminder_time, :dosage, :notes)
            """),
            {
                "user_id": user_id,
                "drug_name": drug_name,
                "reminder_time": t,
                "dosage": dosage,
                "notes": notes,
            },
        )
    await db.commit()

    return {
        "success": True,
        "drug_name": drug_name,
        "reminder_times": times,
        "dosage": dosage,
        "message": f"已设置 {drug_name} 的用药提醒，每天 {' 和 '.join(times)} 提醒您服用 {dosage}",
    }


async def get_health_records(
    db: AsyncSession,
    user_id: str,
    record_type: str = "all",
) -> dict:
    """获取健康档案"""
    records: dict = {}

    if record_type in ("chronic_disease", "all"):
        result = await db.execute(
            text("SELECT disease_name, diagnosed_at, notes FROM chronic_diseases WHERE user_id = :uid"),
            {"uid": user_id},
        )
        records["chronic_diseases"] = [
            {"name": r[0], "diagnosed_at": r[1], "notes": r[2]}
            for r in result.fetchall()
        ]

    if record_type in ("allergy", "all"):
        result = await db.execute(
            text("SELECT allergen, reaction, severity FROM allergies WHERE user_id = :uid"),
            {"uid": user_id},
        )
        records["allergies"] = [
            {"allergen": r[0], "reaction": r[1], "severity": r[2]}
            for r in result.fetchall()
        ]

    if record_type in ("medication", "all"):
        result = await db.execute(
            text("""
                SELECT drug_name, reminder_time, dosage, notes
                FROM medication_reminders WHERE user_id = :uid
            """),
            {"uid": user_id},
        )
        records["medications"] = [
            {"drug": r[0], "time": r[1], "dosage": r[2], "notes": r[3]}
            for r in result.fetchall()
        ]

    return records
