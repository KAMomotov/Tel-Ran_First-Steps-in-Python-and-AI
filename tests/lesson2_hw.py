import pytest

from lesson2.hw import Fan, SmartFanApp, MODE_LABELS, create_run_logger


class FakeClock:
    def __init__(self, t0: float = 0.0):
        self.t = t0

    def now(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def make_app(tmp_path, clock: FakeClock) -> SmartFanApp:
    # Логгер в temp-папку: чтобы тесты не писали “в проект”
    logger = create_run_logger(tmp_path)

    return SmartFanApp(
        logger=logger,
        now=clock.now,
    )


# -----------------------
# Fan: set_mode / status
# -----------------------
def test_fan_set_mode_valid():
    fan = Fan()
    fan.set_mode(3)
    assert fan.mode == 3


def test_fan_set_mode_invalid_raises():
    fan = Fan()
    with pytest.raises(ValueError):
        fan.set_mode(-1)
    with pytest.raises(ValueError):
        fan.set_mode(4)


def test_fan_status_labels():
    fan = Fan()
    for mode, label in MODE_LABELS.items():
        fan.set_mode(mode)
        assert fan.status() == label


# -----------------------
# SmartFanApp: команды
# -----------------------
def test_app_set_mode_changes_history_and_stats(tmp_path):
    clock = FakeClock(100.0)
    app = make_app(tmp_path, clock)

    # старт: mode 0 уже засчитан
    assert app.fan.mode == 0
    assert app.stats.mode_changes[0] == 1

    # смена 0 -> 2
    clock.advance(5.0)
    msg = app.set_mode(2)
    assert "Mode: 2" in msg
    assert app.fan.mode == 2
    assert len(app.history) == 1
    assert app.history[0].old_mode == 0
    assert app.history[0].new_mode == 2
    assert app.stats.mode_changes[2] == 1

    # ещё смена 2 -> 3
    clock.advance(2.0)
    app.set_mode(3)
    assert app.fan.mode == 3
    assert app.stats.mode_changes[3] == 1
    assert len(app.history) == 2


def test_app_up_down_clamped(tmp_path):
    clock = FakeClock(0.0)
    app = make_app(tmp_path, clock)

    # down на 0 не уходит в -1
    assert app.down().startswith("No change") or app.fan.mode == 0
    assert app.fan.mode == 0

    # up до 3 и дальше не растёт
    app.up()
    app.up()
    app.up()
    assert app.fan.mode == 3
    app.up()
    assert app.fan.mode == 3  # clamp


def test_stats_time_and_energy(tmp_path):
    clock = FakeClock(0.0)
    app = make_app(tmp_path, clock)

    # режим 0: 0..10
    clock.advance(10.0)
    app.set_mode(3)  # 0 -> 3

    # режим 3: 10..40
    clock.advance(30.0)
    lines = app.stats_lines()

    # В строках должны быть времена
    joined = "\n".join(lines)
    assert "Time in mode" in joined
    assert "Turbo activations" in joined
    assert "Energy (model)" in joined

    # Проверим, что время в режиме 0 ~10, в режиме 3 ~30
    assert app.stats.time_in_mode_s[0] == pytest.approx(10.0, abs=1e-6)
    assert app.stats.time_in_mode_s[3] == pytest.approx(30.0, abs=1e-6)

    # Энергия должна быть > 0 (т.к. turbo 60W * 30s)
    assert app.stats.energy_wh() > 0.0


def test_history_lines_format(tmp_path):
    clock = FakeClock(1000.0)
    app = make_app(tmp_path, clock)

    clock.advance(1.0)
    app.set_mode(1)
    clock.advance(1.0)
    app.set_mode(2)

    lines = app.history_lines(last=10)
    assert len(lines) == 2
    assert "SET: 0 -> 1" in lines[0]
    assert "SET: 1 -> 2" in lines[1]
