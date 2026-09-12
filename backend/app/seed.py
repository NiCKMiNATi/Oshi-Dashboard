"""Opt-in fictional fixtures. Run with python -m app.seed."""

import argparse
import json
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.config import resolve_database_path
from app.database import create_schema, make_engine
from app.models import Keyword, Oshi, OshiType, Update
from app.schemas import UpdateCreate
from app.scoring import calculate_relevance

DEMO_SOURCE = "Demo fixture (fictional)"
DEMO_NOTICE = "【架空の開発用サンプル・実在する告知ではありません】"
DEMO_OSHI = (
    ("進撃の巨人", OshiType.ANIME, 90, [("進撃の巨人", 1), ("リヴァイ", 25), ("エレン", 25)]),
    ("原神", OshiType.GAME, 80, [("原神", 1), ("ナヒーダ", 25), ("グッズ", 25)]),
    ("Ryujin", OshiType.IDOL, 90, [("RYUJIN", 25), ("リュジン", 25), ("ITZY", 1)]),
)


def demo_updates(today: date) -> list[tuple[str | None, dict]]:
    anchor = datetime.combine(today, time(12), tzinfo=UTC)

    def deadline(days: int) -> datetime:
        return anchor + timedelta(days=days)

    rows = [
        (
            "進撃の巨人",
            "aot-exhibition",
            {
                "title": "[DEMO] 進撃の巨人 原画展・東京会場の入場抽選",
                "summary": "リヴァイとエレンの原画を展示する想定。入場抽選の申込期限を確認。",
                "category": "EVENT",
                "status": "INTERESTED",
                "location": "東京・日本",
                "start_date": today + timedelta(days=21),
                "end_date": today + timedelta(days=35),
                "deadline": deadline(7),
            },
        ),
        (
            "進撃の巨人",
            "aot-levi-merch",
            {
                "title": "[DEMO] リヴァイ アクリルスタンド受注販売",
                "summary": "進撃の巨人の限定グッズを予約する想定。通販の受注締切を記録。",
                "category": "MERCH",
                "status": "SAVED",
                "deadline": deadline(12),
            },
        ),
        (
            "進撃の巨人",
            "aot-screening",
            {
                "title": "[DEMO] 進撃の巨人 特別上映スケジュール",
                "summary": "劇場での特別上映を想定した映画情報。公開日は架空。",
                "category": "MOVIE",
                "status": "NEW",
                "location": "大阪・日本",
                "start_date": today + timedelta(days=28),
            },
        ),
        (
            "原神",
            "genshin-cafe",
            {
                "title": "[DEMO] 原神 コラボカフェ・秋メニュー",
                "summary": "ナヒーダをテーマにしたメニューと来店特典を想定。予約期間を記録。",
                "category": "COLLAB",
                "status": "INTERESTED",
                "location": "東京・日本",
                "start_date": today + timedelta(days=14),
                "end_date": today + timedelta(days=42),
                "deadline": deadline(5),
            },
        ),
        (
            "原神",
            "genshin-nahida-merch",
            {
                "title": "[DEMO] 原神 ナヒーダのぬいぐるみ",
                "summary": "購入済みグッズを管理するためのサンプル。実際の注文は発生しない。",
                "category": "MERCH",
                "status": "BOUGHT",
                "deadline": deadline(-2),
            },
        ),
        (
            "原神",
            "genshin-soundtrack",
            {
                "title": "[DEMO] 原神 サウンドトラック配信",
                "summary": (
                    "ゲーム音楽アルバムの配信日を保存する想定。曲目・日程は未確定の架空情報。"
                ),
                "category": "RELEASE",
                "status": "NEW",
                "start_date": today + timedelta(days=10),
            },
        ),
        (
            "Ryujin",
            "ryujin-tokyo-stage",
            {
                "title": "[DEMO] ITZY RYUJIN 東京公演・先行受付",
                "summary": "リュジンの出演を想定した公演予定。チケット申込の締切を管理。",
                "category": "EVENT",
                "status": "GOING",
                "location": "Tokyo, Japan",
                "start_date": today + timedelta(days=30),
                "end_date": today + timedelta(days=30),
                "deadline": deadline(3),
            },
        ),
        (
            "Ryujin",
            "ryujin-interview",
            {
                "title": "[DEMO] Ryujin インタビュー公開のお知らせ",
                "summary": (
                    "ITZYの活動についてのインタビュー記事を想定。実際の発言の引用は含まない。"
                ),
                "category": "NEWS",
                "status": "NEW",
            },
        ),
        (
            "Ryujin",
            "ryujin-photocard",
            {
                "title": "[DEMO] リュジン フォトカードセット",
                "summary": "RYUJINのグッズ情報を保存する想定。通販受付期間のサンプル。",
                "category": "MERCH",
                "status": "SAVED",
                "deadline": deadline(9),
            },
        ),
        (
            None,
            "unrelated-editorial",
            {
                "title": "[DEMO] Editorial: entertainment industry trends",
                "summary": "推しと関連のない業界コラム。低い関連度と非表示ステータスの確認用。",
                "category": "OTHER",
                "status": "IGNORED",
            },
        ),
    ]
    result = []
    for index, (name, slug, fields) in enumerate(rows):
        fields["summary"] = f"{DEMO_NOTICE} {fields['summary']}"
        result.append(
            (
                name,
                {
                    **fields,
                    "source": DEMO_SOURCE,
                    "source_url": f"https://example.invalid/oshi-demo/{slug}",
                    "published_at": anchor - timedelta(hours=index + 1),
                },
            )
        )
    return result


def seed_database(engine: Engine, today: date | None = None) -> dict[str, int]:
    """Add missing fixtures atomically without changing existing oshi or updates."""
    create_schema(engine)
    counts = {"oshi_added": 0, "updates_added": 0}
    with Session(engine) as session, session.begin():
        by_name = {}
        for name, kind, priority, keywords in DEMO_OSHI:
            oshi = session.scalar(
                select(Oshi).where(Oshi.name == name, Oshi.type == kind).order_by(Oshi.id)
            )
            if oshi is None:
                oshi = Oshi(name=name, type=kind, priority=priority, active=True)
                oshi.keywords = [Keyword(value=value, weight=weight) for value, weight in keywords]
                session.add(oshi)
                counts["oshi_added"] += 1
            by_name[name] = oshi
        session.flush()
        for name, fields in demo_updates(today or datetime.now(UTC).date()):
            if session.scalar(select(Update.id).where(Update.source_url == fields["source_url"])):
                continue
            linked = [by_name[name]] if name else []
            payload = UpdateCreate(**fields, oshi_ids=[oshi.id for oshi in linked])
            update = Update(**payload.model_dump(exclude={"oshi_ids"}), oshi=linked)
            update.relevance_score = calculate_relevance(update)
            session.add(update)
            counts["updates_added"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Add fictional Oshi Dashboard demo data")
    parser.add_argument("--database-path", help="SQLite path; relative to the repository root")
    args = parser.parse_args()
    engine = make_engine(resolve_database_path(args.database_path))
    try:
        print(json.dumps(seed_database(engine), ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
