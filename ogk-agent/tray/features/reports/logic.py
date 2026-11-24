MENU_TEXT = "Hôm nay em đã dùng gì"
TITLE = "OGK - Báo cáo của em"

FAILURE_TEXT = {
    "no_child": "Tài khoản này chưa được gắn với bạn nhỏ nào nên chưa có báo cáo.",
    "not_running": "OGK chưa chạy. Em hãy thử lại sau ít phút.",
    "browser_failed": "Không mở được trình duyệt. Em hãy nhờ bố mẹ giúp nhé.",
}
DEFAULT_FAILURE = "Chưa mở được báo cáo. Em hãy thử lại sau."


def failure_text(code: str) -> str:
    return FAILURE_TEXT.get(code, DEFAULT_FAILURE)
