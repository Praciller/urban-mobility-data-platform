from urban_mobility.config import get_data_dir


def main() -> int:
    print("Urban Mobility Data Platform: Phase 1 bootstrap")
    print(f"DATA_DIR={get_data_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
