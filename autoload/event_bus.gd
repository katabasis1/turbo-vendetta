extends Node
## Глобальные события между сценами и автозагрузками. Только сигналы, без состояния (ARCHITECTURE §5.1).
## Сигнал попадает сюда, только если его слушают в другой сцене или автозагрузке.
## Будут добавлены на своих этапах: race_finished(result: RaceResult) — 1.7 (нужен класс Car из 1.3),
## car_rammed, car_eliminated — 2.3, style_scored — 2.4, currency_changed — 5.5.

@warning_ignore("unused_signal")
signal race_started(track_id: StringName)
@warning_ignore("unused_signal")
signal race_left
