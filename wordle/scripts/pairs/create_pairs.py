import argparse
import json
import requests
import pathlib

from wordhoard import Synonyms, Hypernyms, Hyponyms


def create_pairs(args):
   pass 


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=pathlib.Path,
        help="Path to images",
        required=True,
    )
    parser.add_argument(
        "--difficulty",
        type=float,
        help="Difficulty threshold",
        required=False,
    )
    parser.add_argument(
        "--num_pairs",
        type=int,
        help="Number of pairs",
        required=False,
    )
    parser.add_argument(
        "--per_sysnet",
        type=int,
        help="Number of pairs per Sysnet",
        required=False,
    )
    args = parser.parse_args()
    create_pairs(args)
