#!/usr/bin/env python3
"""
Insert backlinks between current and preview Firefox PN.

Usage:
  python add_privacy_notice_links.py /path/to/repo
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple

# Locale -> link text mapping (from the previous array)
PRIVACY_NOTICE_LINKS: Dict[str, Dict[str, str]] = {
    "cs": {
        "link-to-preview": "Aktualizujeme naše Oznámení o ochraně osobních údajů. Kliknutím sem zobrazíte novou verzi.",
        "link-to-current": "Pro zobrazení našeho aktuálního oznámení klikněte sem.",
    },
    "de": {
        "link-to-preview": "Wir aktualisieren unseren Datenschutzhinweis. Klicken Sie hier, um die neue Version anzuzeigen.",
        "link-to-current": "Zum Anzeigen unseres aktuellen Hinweises hier klicken.",
    },
    "en": {
        "link-to-preview": "We’re updating our Privacy Notice. Click here to see the new version.",
        "link-to-current": "To see our current notice, click here.",
    },
    "es-ES": {
        "link-to-preview": "Estamos actualizando nuestro Aviso de privacidad. Haga clic aquí para ver la nueva versión.",
        "link-to-current": "Para ver nuestro aviso corriente, haga clic aquí.",
    },
    "fr": {
        "link-to-preview": "Nous avons mis à jour notre Politique de confidentialité. Cliquez ici pour voir la nouvelle version.",
        "link-to-current": "Pour consulter notre politique actuelle, cliquez ici.",
    },
    "hu": {
        "link-to-preview": "Frissítjük az adatvédelmi nyilatkozatunkat. Kattintson ide az új verzió megtekintéséhez.",
        "link-to-current": "A jelenlegi nyilatkozat megtekintéséhez kattintson ide.",
    },
    "id": {
        "link-to-preview": "Kami memperbarui Pemberitahuan Privasi kami. Klik di sini untuk melihat versi barunya.",
        "link-to-current": "Untuk melihat pemberitahuan terbaru kami, klik di sini.",
    },
    "it": {
        "link-to-preview": "Stiamo aggiornando la nostra Informativa sulla privacy. Fai clic qui per vedere la nuova versione.",
        "link-to-current": "Per consultare la nostra attuale informativa, fai clic qui.",
    },
    "ja": {
        "link-to-preview": "プライバシーに関する通知を更新しました。新しいバージョンを表示するには、こちらをクリックしてください。",
        "link-to-current": "最新版の通知を表示するには、こちらをクリックします。",
    },
    "nl": {
        "link-to-preview": "We werken onze privacyverklaring bij. Klik hier om de nieuwe versie te bekijken.",
        "link-to-current": "Klik hier als u onze huidige verklaring wilt weergeven.",
    },
    "pl": {
        "link-to-preview": "Aktualizujemy nasze Zasady prywatności. Kliknij tutaj, aby zobaczyć nową wersję.",
        "link-to-current": "Aby zobaczyć aktualne Zasady, kliknij tutaj.",
    },
    "pt-BR": {
        "link-to-preview": "Estamos atualizando nosso Aviso de privacidade. Clique aqui para consultar a nova versão.",
        "link-to-current": "Clique aqui para acessar nosso aviso atual.",
    },
    "ru": {
        "link-to-preview": "Мы обновляем наше Уведомление о конфиденциальности. Нажмите здесь, чтобы ознакомиться с новой версией.",
        "link-to-current": "Для знакомства с нашим текущим уведомлением нажмите здесь.",
    },
    "zh-CN": {
        "link-to-preview": "我们正在更新《隐私声明》。点击此处查看新版本。",
        "link-to-current": "如需查看当前声明，请点击此处。",
    },
}

FIND_ANCHOR = "{: datetime"
SCAN_FIRST_N_LINES = 50


def file_has_class_in_first_lines(
    lines: list[str], class_name: str, n: int = SCAN_FIRST_N_LINES
) -> bool:
    """Return True if any of the first n lines contains class="<class_name>" (single or double quotes)."""
    haystack = "".join(lines[:n])
    return (f'class="{class_name}"' in haystack) or (
        f"class='{class_name}'" in haystack
    )


def find_anchor_index(lines: list[str], anchor: str = FIND_ANCHOR) -> Optional[int]:
    """Return the index of the first line containing the anchor text, else None."""
    for i, line in enumerate(lines):
        if anchor in line:
            return i
    return None


def build_link_line(class_name: str, href: str, text: str) -> str:
    return f'<a class="{class_name}" href="{href}">{text}</a>\n'


def insert_block_after_index(
    lines: list[str], idx: int, link_line: str
) -> tuple[list[str], bool]:
    """
    Insert a block after idx with exactly:
      blank line
      link line
      blank line

    Also removes any existing consecutive blank lines immediately after idx
    so we don't end up with double (or triple) blank lines before the inserted block.
    """
    new_lines = lines[:]
    insert_at = idx + 1

    # Remove ALL consecutive blank lines right after idx
    while insert_at < len(new_lines) and new_lines[insert_at].strip() == "":
        del new_lines[insert_at]

    if not link_line.endswith("\n"):
        link_line += "\n"

    block = ["\n", link_line, "\n"]
    new_lines[insert_at:insert_at] = block
    return new_lines, True


def ensure_link_in_file(
    file_path: Path,
    class_name: str,
    href: str,
    link_text: str,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """
    Ensure the link exists (by class) in the first 50 lines.
    If missing, insert after the first line containing '{: datetime'.
    Returns (changed, message).
    """
    if not file_path.exists():
        return False, f"SKIP (missing): {file_path}"

    try:
        raw = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback if file isn't UTF-8 for some reason.
        raw = file_path.read_text(encoding="utf-8", errors="replace")

    # Keep line endings normalized to '\n' on write; reading splits keeps \n.
    lines = raw.splitlines(keepends=True)

    if file_has_class_in_first_lines(lines, class_name):
        return False, f"OK (already present): {file_path}"

    anchor_idx = find_anchor_index(lines, FIND_ANCHOR)
    if anchor_idx is None:
        return False, f"WARN (anchor not found, no change): {file_path}"

    link_line = build_link_line(class_name, href, link_text)
    new_lines, _ = insert_block_after_index(lines, anchor_idx, link_line)

    if not dry_run:
        file_path.write_text("".join(new_lines), encoding="utf-8")

    return True, f"{'DRY-RUN would update' if dry_run else 'UPDATED'}: {file_path}"


def resolve_locale_dir(root: Path, locale: str) -> Optional[Path]:
    """
    Return the locale directory if it exists, else None.
    Assumes repo structure is strictly root/<locale>.
    """
    loc_dir = root / locale
    return loc_dir if loc_dir.is_dir() else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add missing privacy notice links to locale markdown files."
    )
    parser.add_argument(
        "path", help="Path to the repository root containing one folder per locale."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write changes; only print what would change.",
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: Not a directory: {root}")
        return 2

    total_changed = 0
    total_checked = 0

    for locale, texts in PRIVACY_NOTICE_LINKS.items():
        loc_dir = resolve_locale_dir(root, locale)
        if loc_dir is None:
            print(f"SKIP (locale folder not available): {locale}")
            continue

        # 1) firefox_privacy_notice.md needs link-next-pn (preview/next)
        notice_path = loc_dir / "firefox_privacy_notice.md"
        changed, msg = ensure_link_in_file(
            file_path=notice_path,
            class_name="link-next-pn",
            href="https://www.mozilla.org/privacy/firefox/next",
            link_text=texts["link-to-preview"],
            dry_run=args.dry_run,
        )
        total_checked += 1
        if changed:
            total_changed += 1
        print(f"[{locale}] {msg}")

        # 2) firefox_privacy_notice_preview.md needs link-current-pn (current)
        preview_path = loc_dir / "firefox_privacy_notice_preview.md"
        changed, msg = ensure_link_in_file(
            file_path=preview_path,
            class_name="link-current-pn",
            href="https://www.mozilla.org/privacy/firefox/",
            link_text=texts["link-to-current"],
            dry_run=args.dry_run,
        )
        total_checked += 1
        if changed:
            total_changed += 1
        print(f"[{locale}] {msg}")

    print(f"\nDone. Checked: {total_checked} file targets. Changed: {total_changed}.")
    if args.dry_run:
        print("Dry-run mode: no files were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
