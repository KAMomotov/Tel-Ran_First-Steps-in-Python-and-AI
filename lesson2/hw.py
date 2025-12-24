from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import logging
import time


# =========================
# Константы / доменные данные
# =========================

MODE_LABELS: dict[int, str] = {
    0: "switched off",
    1: "speed 1",
    2: "speed 2",
    3: "turbo mode",
}

# Условная мощность (ватты) по режимам — чтобы посчитать “потребление”.
# (Это модель/симуляция, а не реальная физика конкретного вентилятора.)
MODE_WATTS: dict[int, int] = {
    0: 0,
    1: 20,
    2: 35,
    3: 60,
}

MIN_MODE = 0
MAX_MODE = 3


# =========================
# Доменные структуры
# =========================

@dataclass(frozen=True)
class Event:
    timestamp: float
    action: str
    old_mode: int
    new_mode: int


@dataclass
class Fan:
    """Состояние вентилятора. Отвечает за режим и его проверку."""
    mode: int = 0

    def set_mode(self, new_mode: int) -> None:
        # Сравнения + логика
        if new_mode < MIN_MODE or new_mode > MAX_MODE:
            raise ValueError(f"Mode must be from {MIN_MODE} to {MAX_MODE}")
        self.mode = new_mode

    def status(self) -> str:
        # Принадлежность (membership)
        return MODE_LABELS[self.mode] if self.mode in MODE_LABELS else "unknown mode"


@dataclass
class Stats:
    """
    Считает статистику:
    - сколько раз включали каждый режим
    - сколько времени провели в режимах (секунды)
    - энергию (Вт⋅ч) по модели MODE_WATTS
    """
    mode_changes: dict[int, int] = field(default_factory=lambda: {m: 0 for m in MODE_LABELS})
    time_in_mode_s: dict[int, float] = field(default_factory=lambda: {m: 0.0 for m in MODE_LABELS})
    _last_mode: int = 0
    _last_ts: Optional[float] = None

    def start(self, initial_mode: int, ts: float) -> None:
        self._last_mode = initial_mode
        self._last_ts = ts
        # стартовый режим считаем “включённым” 1 раз
        if initial_mode in self.mode_changes:
            self.mode_changes[initial_mode] += 1

    def on_mode_change(self, old_mode: int, new_mode: int, ts: float) -> None:
        if self._last_ts is not None:
            self.time_in_mode_s[old_mode] += ts - self._last_ts

        self._last_mode = new_mode
        self._last_ts = ts

        if new_mode in self.mode_changes:
            self.mode_changes[new_mode] += 1

    def finalize(self, ts: float) -> None:
        if self._last_ts is None:
            return
        self.time_in_mode_s[self._last_mode] += ts - self._last_ts
        self._last_ts = ts

    def turbo_count(self) -> int:
        return self.mode_changes.get(3, 0)

    def energy_wh(self) -> float:
        # Энергия Wh = sum( Watts * hours )
        total = 0.0
        for mode, seconds in self.time_in_mode_s.items():
            watts = MODE_WATTS.get(mode, 0)
            total += watts * (seconds / 3600.0)
        return total


# =========================
# Логгер на запуск (файл)
# =========================

def create_run_logger(log_dir: str | Path = "logs") -> logging.Logger:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Микросекунды -> уникально для быстрых тестов
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = log_path / f"run_{ts}.log"

    logger = logging.getLogger(f"SmartFanRun_{ts}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # сохраним путь к лог-файлу, чтобы export мог положить файл рядом
    logger.log_file = filename  # type: ignore[attr-defined]

    if not logger.handlers:
        handler = logging.FileHandler(filename, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.info("START")
    logger.info("Log file: %s", filename)
    return logger


# =========================
# Контроллер приложения
# =========================

@dataclass
class SmartFanApp:
    fan: Fan = field(default_factory=Fan)
    stats: Stats = field(default_factory=Stats)
    history: list[Event] = field(default_factory=list)

    logger: logging.Logger = field(default_factory=create_run_logger)
    now: Callable[[], float] = field(default_factory=lambda: time.time)

    def __post_init__(self) -> None:
        ts = self.now()
        self.stats.start(self.fan.mode, ts)
        self.logger.info("Initial mode: %s (%s)", self.fan.mode, self.fan.status())

    def _log_event(self, action: str, old_mode: int, new_mode: int) -> None:
        ts = self.now()
        self.history.append(Event(ts, action, old_mode, new_mode))
        self.logger.info("%s | %s -> %s", action, old_mode, new_mode)

    def _change_mode(self, new_mode: int, action: str) -> str:
        old_mode = self.fan.mode
        if new_mode == old_mode:
            return f"No change: {old_mode} ({self.fan.status()})"

        self.fan.set_mode(new_mode)
        ts = self.now()
        self.stats.on_mode_change(old_mode, new_mode, ts)
        self._log_event(action, old_mode, new_mode)
        return f"Mode: {self.fan.mode} ({self.fan.status()})"

    def set_mode(self, new_mode: int) -> str:
        return self._change_mode(new_mode, action="SET")

    def up(self) -> str:
        # Присваивание с операторами (+=) — по сути то же самое, что mode = mode + 1
        new_mode = self.fan.mode + 1
        if new_mode > MAX_MODE:
            new_mode = MAX_MODE
        return self._change_mode(new_mode, action="UP")

    def down(self) -> str:
        new_mode = self.fan.mode - 1
        if new_mode < MIN_MODE:
            new_mode = MIN_MODE
        return self._change_mode(new_mode, action="DOWN")

    def status(self) -> str:
        return f"Mode: {self.fan.mode} ({self.fan.status()})"

    def history_lines(self, last: int = 10) -> list[str]:
        items = self.history[-last:]
        lines: list[str] = []
        for e in items:
            stamp = datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S")
            lines.append(f"{stamp} | {e.action}: {e.old_mode} -> {e.new_mode}")
        return lines

    def stats_lines(self) -> list[str]:
        self.stats.finalize(self.now())
        lines: list[str] = []
        lines.append("Stats:")
        lines.append("  Mode changes:")
        for mode in sorted(MODE_LABELS):
            lines.append(f"    {mode} ({MODE_LABELS[mode]}): {self.stats.mode_changes[mode]}")
        lines.append("  Time in mode (seconds):")
        for mode in sorted(MODE_LABELS):
            lines.append(f"    {mode} ({MODE_LABELS[mode]}): {self.stats.time_in_mode_s[mode]:.1f}s")
        lines.append(f"  Turbo activations: {self.stats.turbo_count()}")
        lines.append(f"  Energy (model): {self.stats.energy_wh():.2f} Wh")
        return lines

    def current_power_w(self) -> int:
        return MODE_WATTS.get(self.fan.mode, 0)

    def power_lines(self) -> list[str]:
        # обновим накопленное время/энергию до текущего момента
        self.stats.finalize(self.now())
        return [
            "Power:",
            f"  Mode: {self.fan.mode} ({self.fan.status()})",
            f"  Current: {self.current_power_w()} W",
            f"  Energy (model): {self.stats.energy_wh():.2f} Wh",
        ]

    def export_stats(self) -> Path:
        """
        Пишет статистику в файл рядом с логом запуска.
        Возвращает путь к экспортированному файлу.
        """
        log_file: Path = getattr(self.logger, "log_file", Path("run.log"))  # type: ignore[assignment]
        export_file = log_file.with_name(f"{log_file.stem}_stats.txt")

        content_lines: list[str] = []
        content_lines.extend(self.stats_lines())
        content_lines.append("")
        content_lines.append("History (last 50):")
        content_lines.extend(self.history_lines(last=50) or ["<empty>"])

        export_file.write_text("\n".join(content_lines) + "\n", encoding="utf-8")
        self.logger.info("EXPORT | %s", export_file)
        return export_file

    @staticmethod
    def help_text() -> str:
        return (
            "Commands:\n"
            "  0..3      - set mode\n"
            "  up        - increase mode by 1 (max 3)\n"
            "  down      - decrease mode by 1 (min 0)\n"
            "  status    - show current mode\n"
            "  power     - show current watts and accumulated Wh\n"
            "  history   - show last 10 changes\n"
            "  stats     - show statistics (time, turbo count, energy)\n"
            "  export    - save stats to a file next to the log\n"
            "  help      - show this help\n"
            "  q / quit  - exit\n"
        )



# =========================
# CLI
# =========================

def run_cli(
    app: SmartFanApp,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> None:
    output_func("Smart Fan Controller. Type 'help' to see commands.")

    while True:
        raw = input_func("> ").strip().lower()

        # membership
        if raw in {"q", "quit"}:
            app.logger.info("QUIT")
            output_func("Bye!")
            return

        if raw == "help":
            output_func(app.help_text())
            continue

        if raw == "status":
            output_func(app.status())
            continue

        if raw == "up":
            output_func(app.up())
            continue

        if raw == "down":
            output_func(app.down())
            continue

        if raw == "history":
            lines = app.history_lines()
            if not lines:
                output_func("No history yet.")
            else:
                output_func("\n".join(lines))
            continue

        if raw == "stats":
            output_func("\n".join(app.stats_lines()))
            continue

        if raw == "power":
            output_func("\n".join(app.power_lines()))
            continue

        if raw == "export":
            path = app.export_stats()
            output_func(f"Exported to: {path}")
            continue

        # режим 0..3
        if raw.isdigit():
            mode = int(raw)
            try:
                output_func(app.set_mode(mode))
            except ValueError as exc:
                output_func(f"Invalid mode: {exc}")
            continue

        output_func("Unknown command. Type 'help'.")


def main() -> None:
    app = SmartFanApp()
    run_cli(app)


if __name__ == "__main__":
    main()
