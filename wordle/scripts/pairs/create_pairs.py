import argparse
import json
import requests
import pathlib
import os
import time
import random
import re
import uuid

from collections import ChainMap

from wordhoard import Synonyms, Hypernyms


def _build_syn_hyp_list(words: list, weight: float):
    word_list = []
    if isinstance(words, list):
        if "spelled correctly" in words[0]:
            word_list = []
        else:
            for word in words:
                word_list.append({word: weight})
    return dict(ChainMap(*word_list))


def get_syn_hyper(word: str):
    """
        A function to all the wordhoard related APIs and retrieve a given word's
    synonyms and hypernyms"
    """
    synonym = Synonyms(search_string=word)
    hypernym = Hypernyms(search_string=word)

    synonyms = synonym.find_synonyms()
    hypernyms = hypernym.find_hypernyms()

    syn_list = _build_syn_hyp_list(synonyms, 0.8)
    hyper_list = _build_syn_hyp_list(hypernyms, 0.6)
    return syn_list, hyper_list


def get_related_terms(word: str):
    """
        This function calls the ConceptNet API and gets the 10 most related
    terms and their weights.
    """
    obj = requests.get(
        "https://api.conceptnet.io/related/c/en/" + word + "?filter=/c/en"
    ).json()
    terms = []
    for term in obj["related"]:
        terms.append(
            {term.get("@id").split("/")[-1].replace("_", " "): term.get("weight")}
        )
    return dict(ChainMap(*terms))


def generate_file(sysnets_words: list):
    """
        This function takes the words associated with each sysnet and generates a
    file with their synonyms, hypernims, hyponims and weighted related terms from
    ConceptNet. Some APIs have a very low limit on calls, and a long wait time
    is necessary, additionally because of a bug in the library."
    """
    term_list = []
    filename = str(uuid.uuid4()) + ".json"
    file_path = os.getcwd() + "/" + filename

    print("Number of words to process: ", len(sysnets_words))
    for num_word, word in enumerate(sysnets_words[:20]):
        related_terms = get_related_terms(word[1])
        synonyms, hypernyms = get_syn_hyper(word[1])

        term_list.append(
            [
                {"Sysnet": word[0]},
                {"Word": {word[1]: 1}},
                {"Synonyms": synonyms},
                {"Hypernyms": hypernyms},
                {"ConceptNet related terms": related_terms},
            ]
        )

        time.sleep(3)
        print("Processed word number ", num_word + 1, " : ", word[1])
    with open(filename, "w", encoding="utf-8") as terms_file:
        json.dump(
            term_list,
            terms_file,
            ensure_ascii=False,
            indent=4,
        )
    print("All the words finished processing!")
    print("Path to file: ", file_path)
    return file_path


def sysnet_to_word(path: pathlib.Path):
    """
        This function generates a list of available sysnets in the image directory
    and their idenfifying words. It takes the path ts the image directory and the
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


def _preprocess_terms(terms: list):
    all_terms = []
    for term in terms:
        trimmed = []
        for term_types in term[1:]:
            for key, val in term_types.items():
                for k, v in val.items():
                    if len(k) == 5:
                        for d in trimmed:
                            if k in d:
                                v = round(((v + d.get(k)) / 2), 3)
                                trimmed.remove(d)
                        trimmed.append({k: v})
        all_terms.append([*term[0].values(), dict(ChainMap(*trimmed))])
    return all_terms


def create_pairs(args: argparse.Namespace):
    """
        The main function to create the pairs. Retrieves the sysnets, words and all
    required related terms, then makes custom defined pairs according to the
    parameters passed to the script. To skip the generation and go direclty to
    pair creation, a generated terms file needs to be passed.
    """
    terms_file = ""
    if not args.terms_path:
        sysnets_words = sysnet_to_word(args.image_path)
        terms_file = generate_file(sysnets_words)
    else:
        terms_file = args.terms_path

    with open(terms_file, "r") as terms:
        possible_pairs = _preprocess_terms(json.loads(terms.read()))

    temp_pars = []
    if args.difficulty:
        diff_terms = []
        for sys in possible_pairs:
            trimmed = []
            for k, v in sys[1].items():
                if sys[1].get(k) >= args.difficulty:
                    trimmed.append({k: v})
            if trimmed:
                diff_terms.append([sys[0], dict(ChainMap(*trimmed))])
        temp_pairs = diff_terms
    else:
        temp_pairs = possible_pairs

    if args.per_sysnet:
        reduced_terms = []
        for sys in temp_pairs:
            reduced_terms.append(
                [sys[0], {k: sys[1][k] for k in list(sys[1])[: args.per_sysnet]}]
            )
        temp_pairs = reduced_terms

    if args.num_sysnets:
        temp_pairs = [random.choice(temp_pairs) for _ in range(args.num_sysnets)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image_path",
        type=pathlib.Path,
        help="Path to images",
        required=True,
    )
    parser.add_argument(
        "--terms_path",
        type=pathlib.Path,
        help="Path to generated terms file",
        required=False,
    )
    parser.add_argument(
        "--difficulty",
        type=float,
        help="Difficulty threshold",
        required=False,
    )
    parser.add_argument(
        "--num_sysnets",
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
