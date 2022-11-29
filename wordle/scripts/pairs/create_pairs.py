import argparse
import json
import requests
import pathlib
import os
import time
import re

from collections import defaultdict

from wordhoard import Synonyms, Hypernyms


def get_syn_hyper(word: str):
    """
        A function to all the wordhoard related APIs and retrieve a given word's
    synonyms and hypernyms"
    """
    synonym = Synonyms(search_string=word)
    hypernym = Hypernyms(search_string=word)

    synonyms = synonym.find_synonyms()
    hypernyms = hypernym.find_hypernyms()

    if any("No synonyms" in s for s in synonyms):
        synonyms = []
    if any("No hypernyms" in s for s in hypernyms):
        hypernyms = []

    return synonyms, hypernyms


def get_related_terms(word: str):
    """
        This function calls the ConceptNet API and gets the 10 most related
    terms and their weights.
    """
    obj = requests.get(
        "https://api.conceptnet.io/related/c/en/" + word + "?filter=/c/en"
    ).json()
    return obj["related"]


def generate_file(sysnets_words: list):
    """
        This function takes the words associated with each sysnet and generates a
    file with their synonyms, hypernims, hyponims and weighted related terms from
    ConceptNet. Some APIs have a very low limit on calls, and a long wait time
    is necessary, additionally because of a bug in the library."
    """
    term_list = []
    print("Number of words to process: ", len(sysnets_words))
    for num_word, word in enumerate(sysnets_words):
        related_terms = get_related_terms(word[1])
        synonyms, hypernyms = get_syn_hyper(word[1])
        term_list.append(
            [
                word[0],
                word[1],
                synonyms,
                hypernyms,
                related_terms,
            ]
        )
        time.sleep(3)
        print("Processed word number ", num_word + 1, " : ", word[1])
        print(term_list[-1])
    print("All the words finished processing!")
    print("File is available at: ")
    return term_list


def sysnet_to_word(path: pathlib.Path):
    """
        This function generates a list of available sysnets in the image directory
    and their idenfifying words. It takes the path to the image directory and the
    file that lists all available ImageNet words, then creates a joint list.
    """
    cur_dir = os.getcwd()

    os.chdir(path)
    sysnets = [name for name in os.listdir(".") if os.path.isdir(name)]

    os.chdir(cur_dir)
    lines = [
        re.split(r"[ ]*[,\t\n][ ]*", x.strip()) for x in open("words.txt").readlines()
    ]
    sysnets_words = []
    for line in lines:
        for sysnet in sysnets:
            if sysnet == line[0]:
                sysnets_words.append([line[0], line[1]])
    return sysnets_words


def create_pairs(args: argparse.Namespace):
    """
        The main function to create the pairs. Retrieves the sysnets, words and all
    required related terms, then makes custom defined pairs according to the
    parameters passed to the script.
    """
    sysnets_words = sysnet_to_word(args.path)
    generate_file(sysnets_words)


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
