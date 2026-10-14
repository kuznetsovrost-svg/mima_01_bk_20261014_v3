#!/usr/bin/env python3
"""
Главный модуль скилла idef0-excalidraw.
Предоставляет CLI для валидации, генерации каталога и описаний.
"""

import argparse
import sys
import json
from pathlib import Path

# Импорт модулей скилла
from excalidraw_parser import ExcalidrawParser
from block_extractor import BlockExtractor
from arrow_extractor import ArrowExtractor
from side_detector import SideDetector
from icom_checker import ICOMChecker
from tunnel_detector import TunnelDetector
from catalogue_generator import CatalogueGenerator
from description_generator import DescriptionGenerator


def cmd_validate(args):
    """Команда: валидация IDEF0 диаграммы."""
    parser = ExcalidrawParser(args.file)
    if not parser.load():
        print(f"Error: Cannot load {args.file}")
        return 1

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    errors = []
    warnings = []

    # 1. Проверка базовой структуры
    if not blocks:
        errors.append("No IDEF0 blocks found")
    if not arrows:
        warnings.append("No arrows found")

    # 2. Проверка каждого блока
    for block in blocks:
        if not block.get('name'):
            errors.append(f"Block {block.get('number', '?')} has no name")
        if not block.get('number'):
            warnings.append(f"Block '{block.get('name', '?')}' has no number")

    # 3. Проверка стрелок
    for arrow in arrows:
        if not arrow.get('arrow_name'):
            warnings.append(f"Arrow {arrow.get('id', '?')} has no name")

    # 4. ICOM consistency (если указан parent)
    icom_errors = []
    if args.parent:
        checker = ICOMChecker(blocks, arrows, parser.frames)
        icom_errors = checker.check_consistency(args.parent)

    # Отчёт
    print(f"=== Валидация {args.file} ===\n")
    print(f"Blocks: {len(blocks)}")
    print(f"Arrows: {len(arrows)}")
    print(f"Frames: {len(parser.frames)}")
    print()

    if errors:
        print(f"❌ Errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    else:
        print("✅ No structural errors")

    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warn in warnings:
            print(f"  - {warn}")

    if icom_errors:
        print(f"\n🔗 ICOM consistency issues ({len(icom_errors)}):")
        for err in icom_errors:
            print(f"  - {err.get('message', err)}")

    return 0 if not errors else 1


def cmd_generate_catalogue(args):
    """Команда: генерация каталога объектов."""
    parser = ExcalidrawParser(args.file)
    if not parser.load():
        print(f"Error: Cannot load {args.file}")
        return 1

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    frame = None
    if args.frame:
        for f in parser.frames:
            if f.get('name') == args.frame or f.get('id') == args.frame:
                frame = f
                break
        if not frame:
            print(f"Error: Frame '{args.frame}' not found")
            return 1

    generator = CatalogueGenerator(blocks, arrows, frame)
    catalogue = generator.generate_catalogue()
    table = generator.format_catalogue_table(catalogue)

    print(f"=== Каталог объектов: {args.frame or 'all'} ===\n")
    print(table)

    return 0


def cmd_check_icom(args):
    """Команда: проверка ICOM consistency."""
    parser = ExcalidrawParser(args.file)
    if not parser.load():
        print(f"Error: Cannot load {args.file}")
        return 1

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    checker = ICOMChecker(blocks, arrows, parser.frames)
    errors = checker.check_consistency(args.parent)

    print(f"=== ICOM Consistency: parent={args.parent} ===\n")

    if not errors:
        print("✅ ICOM consistency: OK")
        return 0

    print(f"❌ Found {len(errors)} issues:")
    for err in errors:
        print(f"  [{err.get('severity', '?').upper()}] {err.get('message', err)}")

    return 1


def cmd_generate_description(args):
    """Команда: генерация описаний блоков."""
    parser = ExcalidrawParser(args.file)
    if not parser.load():
        print(f"Error: Cannot load {args.file}")
        return 1

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    generator = DescriptionGenerator(blocks, arrows)
    descriptions = generator.generate_all_descriptions()

    print(f"=== Описания блоков ===\n")
    print(descriptions)

    return 0


def cmd_summary(args):
    """Команда: краткая сводка по диаграмме."""
    parser = ExcalidrawParser(args.file)
    if not parser.load():
        print(f"Error: Cannot load {args.file}")
        return 1

    summary = parser.summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()
    detector = TunnelDetector(arrows)
    tunnels = detector.find_all_tunnels()

    print(f"\nTunnels: {len(tunnels)}")
    for t in tunnels:
        print(f"  - {t['arrow_name']} ({t['tunnel_side']})")

    return 0


def main():
    """Главная функция CLI."""
    parser = argparse.ArgumentParser(
        description="IDEF0 + Excalidraw анализатор",
        prog="idef0-validate"
    )
    parser.add_argument('--file', required=True, help='Path to .excalidraw file')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # validate
    sub_validate = subparsers.add_parser('validate', help='Validate IDEF0 diagram')
    sub_validate.add_argument('--parent', help='Parent block ID for ICOM check')

    # generate-catalogue
    sub_cat = subparsers.add_parser('generate-catalogue', help='Generate arrow catalogue')
    sub_cat.add_argument('--frame', help='Frame name to generate for')

    # check-icom
    sub_icom = subparsers.add_parser('check-icom', help='Check ICOM consistency')
    sub_icom.add_argument('--parent', required=True, help='Parent block ID')

    # generate-description
    sub_desc = subparsers.add_parser('generate-description',
                                       help='Generate block descriptions')

    # summary
    sub_sum = subparsers.add_parser('summary', help='Show diagram summary')

    args = parser.parse_args()

    commands = {
        'validate': cmd_validate,
        'generate-catalogue': cmd_generate_catalogue,
        'check-icom': cmd_check_icom,
        'generate-description': cmd_generate_description,
        'summary': cmd_summary,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
