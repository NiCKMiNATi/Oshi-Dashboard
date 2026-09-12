# Relevance scoring

`app/scoring.py` implements the requested weights. Each signal contributes at most once per update, then the result is clamped to 0–100. Scores are calculated by the backend; requests supplying `relevance_score` are rejected.

The original contract gives weights but not signal detection rules. These are the explicit v0.1 interpretations:

| Signal | Points | Detection |
| --- | ---: | --- |
| Followed oshi | +40 | At least one explicitly linked oshi has `active=true`. |
| Priority keyword | +25 | At least one keyword with `weight>0` belonging to an active linked oshi appears in the title or summary. |
| Japan event | +20 | Category is `EVENT` and location matches a supported Japan/city marker. |
| Action deadline | +20 | `deadline` is present. |
| Merchandise | +10 | Category is `MERCH`. |
| Irrelevant editorial | −30 | No active linked oshi, and the title contains an editorial marker. |

Keyword matching uses Unicode NFKC normalization, case folding, and substring matching, including Japanese. Keyword weights are 0–100: zero disables the bonus, any positive value enables the fixed +25. Weight magnitudes and oshi priority are retained for later ranking work; neither changes the specified bonus. Multiple oshi, multiple matching keywords, or repeated text do not stack points.

Japan location markers include `日本`, `東京`, `大阪`, `横浜`, `京都`, `名古屋`, `福岡`, `札幌`, `神戸`, `千葉`, `埼玉`, `仙台`, `広島`, `沖縄`; their unaccented English names; `Japan`; and `JP`. English markers require word boundaries. This is a small explicit heuristic, not geographic inference. Locations elsewhere, online-only locations, and missing locations receive no bonus. `COLLAB` and `MOVIE` do not receive the event bonus in v0.1.

Editorial markers are the words `opinion` / `editorial`, or `コラム` / `考察` in the title. An editorial linked to an active oshi is treated as relevant and does not receive the penalty. No semantic classifier or ingestion service is involved.

Deadlines contribute even if already past. The score expresses relevance, not current urgency, and has no clock dependency. A future urgency feature can handle expiry separately. Dates and location may be cleared with `null`; removing the deadline removes its points.

Examples:

- Followed oshi + keyword + Japan event + deadline: 40 + 25 + 20 + 20 = 105 → **100**.
- Followed oshi + keyword + merchandise + deadline: 40 + 25 + 10 + 20 = **95**.
- Unrelated editorial: −30 → **0**.

Create/update content operations, oshi keyword/active changes, and oshi deletion recompute affected scores in the same transaction. The status-only endpoint leaves the score unchanged. Changes made directly through raw SQL bypass application scoring; normal edits should use the API.
