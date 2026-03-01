import argparse
from engine.exoneural_governor.helper import run

def main():
    p = argparse.ArgumentParser(description='runner cli')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    run(args.out)

if __name__ == '__main__':
    main()
