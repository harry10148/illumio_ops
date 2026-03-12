import os
import sys
import logging
import unicodedata
import re
from logging.handlers import RotatingFileHandler
from src.i18n import t, get_language

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_LAST_INPUT_ACTION = "value"


def get_last_input_action() -> str:
    return _LAST_INPUT_ACTION


def _set_last_input_action(action: str):
    global _LAST_INPUT_ACTION
    _LAST_INPUT_ACTION = action


class Colors:
    """ANSI color codes. Auto-disabled when stdout is not a TTY (daemon/service mode)."""

    _enabled = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    HEADER = "\033[95m" if _enabled else ""
    BLUE = "\033[94m" if _enabled else ""
    CYAN = "\033[96m" if _enabled else ""
    GREEN = "\033[92m" if _enabled else ""
    WARNING = "\033[93m" if _enabled else ""
    FAIL = "\033[91m" if _enabled else ""
    DARK_GRAY = "\033[90m" if _enabled else ""
    ENDC = "\033[0m" if _enabled else ""
    BOLD = "\033[1m" if _enabled else ""
    UNDERLINE = "\033[4m" if _enabled else ""


def safe_input(
    prompt: str,
    value_type=str,
    valid_range=None,
    allow_cancel=True,
    hint=None,
    help_text=None,
):
    if help_text:
        print(f"{Colors.DARK_GRAY}{help_text}{Colors.ENDC}")

    if prompt.startswith("\n"):
        prefix = "\n"
        prompt = prompt[1:]
    else:
        prefix = ""

    range_hint = ""
    if valid_range:
        try:
            vals = sorted(list(valid_range))
            if vals and all(isinstance(v, int) for v in vals):
                if vals == list(range(vals[0], vals[-1] + 1)):
                    range_hint = f" [{vals[0]}-{vals[-1]}]"
                else:
                    range_hint = " [" + ",".join(str(v) for v in vals) + "]"
            else:
                range_hint = " [" + ",".join(str(v) for v in vals) + "]"
        except Exception:
            range_hint = ""

    full_prompt = f"{prefix}{Colors.CYAN}[?]{Colors.ENDC} {prompt}{range_hint}"
    if hint:
        def_text = t("def_val_prefix", default="Default")
        full_prompt += f" {Colors.DARK_GRAY}({def_text}: {hint}){Colors.ENDC}"

    shortcuts = ""
    lang = get_language()
    if allow_cancel:
        if lang == "zh_TW":
            shortcuts = "Enter預設, 0返回, -1取消, h說明"
        else:
            shortcuts = t(
                "cli_shortcuts_full",
                default="Enter=default, 0=back, -1=cancel, h=help",
            )
    else:
        if lang == "zh_TW":
            shortcuts = "Enter預設, h說明"
        else:
            shortcuts = t("cli_shortcuts_no_cancel", default="Enter=default, h=help")

    full_prompt += f" {Colors.DARK_GRAY}[{shortcuts.strip()}]{Colors.ENDC}"
    full_prompt += f" {Colors.GREEN}❯{Colors.ENDC} "

    while True:
        try:
            raw = input(full_prompt).strip()

            if raw.lower() in ["h", "?"]:
                _set_last_input_action("help")
                if help_text:
                    print(f"{Colors.DARK_GRAY}{help_text}{Colors.ENDC}")
                else:
                    help_text_fallback = (
                        "此欄位沒有額外說明。"
                        if lang == "zh_TW"
                        else "No extra help for this field."
                    )
                    print(
                        f"{Colors.DARK_GRAY}{t('cli_no_field_help', default=help_text_fallback)}{Colors.ENDC}"
                    )
                continue

            if not raw:
                # User hit Enter without typing anything
                _set_last_input_action("empty")
                return ""

            # Standardize 0 and -1 for cancel/back ONLY if explicitly typed
            if allow_cancel and raw == "0":
                _set_last_input_action("back")
                return None

            if allow_cancel and raw == "-1":
                _set_last_input_action("cancel")
                return None

            val = value_type(raw)
            if valid_range and val not in valid_range:
                _set_last_input_action("invalid")
                print(
                    f"{Colors.FAIL}{t('error_out_of_range', default='Value out of range.')}{Colors.ENDC}"
                )
                continue
            _set_last_input_action("value")
            return val
        except ValueError:
            _set_last_input_action("invalid")
            print(
                f"{Colors.FAIL}{t('error_format', default='Invalid format.')}{Colors.ENDC}"
            )


def setup_logger(
    name: str,
    log_file: str,
    level=logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


def format_unit(value, type="volume") -> str:
    try:
        val = float(value)
    except (ValueError, TypeError):
        return str(value)

    if type == "volume":
        if val >= 1024 * 1024:
            return f"{val / (1024 * 1024):.2f} TB"
        if val >= 1024:
            return f"{val / 1024:.2f} GB"
        return f"{val:.2f} MB"
    elif type == "bandwidth":
        if val >= 1000:
            return f"{val / 1000:.2f} Gbps"
        return f"{val:.2f} Mbps"
    return str(val)


def get_visible_width(s: str) -> int:
    """Calculate the exact visible width of a string on screen, ignoring ANSI codes."""
    clean_s = ANSI_ESCAPE.sub("", str(s))
    width = 0
    for char in clean_s:
        status = unicodedata.east_asian_width(char)
        # In Traditional Chinese (cp950) Windows environments, Ambiguous (A) chars usually take 2 spaces.
        width += 2 if status in ("W", "F", "A") else 1
    return width


def pad_string(s: str, total_width: int, fillchar: str = " ") -> str:
    """Pad string to a specific display width considering CJK characters."""
    current_width = get_visible_width(s)
    if current_width >= total_width:
        return s
    return s + fillchar * (total_width - current_width)


def draw_panel(title: str, lines: list, width: int = 80):
    """Draws a modern UI panel in the terminal using ASCII characters."""
    b = Colors.DARK_GRAY
    e = Colors.ENDC
    content = []

    # Header
    content.append(f"{b}+-{'-' * (width - 2)}+{e}")

    # Title row (centered)
    t_width = get_visible_width(title)
    if t_width <= width - 4:
        pad = width - 4 - t_width
        left_pad = pad // 2
        right_pad = pad - left_pad
        content.append(
            f"{b}|{e} {' ' * left_pad}{Colors.BOLD}{Colors.CYAN}{title}{e}{' ' * right_pad} {b}|{e}"
        )
    else:
        content.append(f"{b}|{e} {Colors.BOLD}{Colors.CYAN}{title}{e} {b}|{e}")

    content.append(f"{b}+-{'-' * (width - 2)}+{e}")

    # Lines
    for line in lines:
        if line == "-":
            content.append(f"{b}+-{'-' * (width - 2)}+{e}")
            continue

        real_width = get_visible_width(line)
        if real_width <= width - 4:
            pad = width - 4 - real_width
            content.append(f"{b}|{e} {line}{' ' * pad} {b}|{e}")
        else:
            content.append(f"{b}|{e} {line} {b}|{e}")

    # Footer
    content.append(f"{b}+-{'-' * (width - 2)}+{e}")

    print("\n".join(content))


def draw_table(headers: list, rows: list):
    """Draws a modern UI table in the terminal using ASCII characters."""
    if not headers and not rows:
        return

    cols_width = [get_visible_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(cols_width):
                w = get_visible_width(cell)
                if w > cols_width[i]:
                    cols_width[i] = w

    # Add padding
    cols_width = [w + 2 for w in cols_width]

    b = Colors.DARK_GRAY
    e = Colors.ENDC

    def draw_sep(left, mid, right):
        seps = [f"{'-' * w}" for w in cols_width]
        return f"{b}{left}{mid.join(seps)}{right}{e}"

    def draw_row(row_data, is_header=False):
        cells = []
        for i, cell in enumerate(row_data):
            if i >= len(cols_width):
                continue
            cell_str = str(cell)
            w = get_visible_width(cell_str)
            pad = cols_width[i] - w - 1
            content = f"{Colors.CYAN}{cell_str}{e}" if is_header else f"{cell_str}"
            cells.append(f" {content}{' ' * pad}")
        line = f"{b}|{e}".join(cells)
        return f"{b}|{e}{line}{b}|{e}"

    print(draw_sep("+-", "-+-", "-+"))
    print(draw_row(headers, is_header=True))
    print(draw_sep("+-", "-+-", "-+"))

    for row in rows:
        print(draw_row(row))

    print(draw_sep("+-", "-+-", "-+"))
