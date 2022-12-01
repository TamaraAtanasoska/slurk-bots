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

from profanity_check import predict_prob
from wordhoard import Synonyms, Hypernyms


def _build_syn_hyp_list(words: list, weight: float):
    """
    This function gives shape to the retrieved synonyms and hypernyms. It takes a
    given list of words and a set weight for all words of type and makes word:weight
    pairs. Additionally, there is profanity check.
    """
    word_list = []
    if isinstance(words, list):
        if "spelled correctly" in words[0]:
            word_list = []
        else:
            for word in words:
                if predict_prob([word]) < 0.5:
                    word_list.append({word: weight})
    return dict(ChainMap(*word_list))


def get_syn_hyper(word: str):
    """
        A function to all the wordhoard related APIs and retrieve a given word's
    synonyms and hypernyms.
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
        word = term.get("@id").split("/")[-1].replace("_", " ")
        if predict_prob([word]) < 0.5:
            terms.append({word: term.get("weight")})
    return dict(ChainMap(*terms))


def generate_file(sysnets_words: list):
    """
        This function takes the words associated with each sysnet and generates a
    file with their synonyms, hypernims, hyponims and weighted related terms from
    ConceptNet. Some APIs have a very low limit on calls, and a long wait time
    is necessary, additionally because of a bug in the library."
    """
    term_list = []
    filename = str("terms_" + str(uuid.uuid4())) + ".json"
    file_path = os.getcwd() + "/" + filename

    print("Number of words to process: ", len(sysnets_words))
    for num_word, word in enumerate(sysnets_words):
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
    print("Path to full terms file: ", file_path)
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
    """
    This function reduceds all the related words to just the possible pairs with 5
    letters. Additionally whenever there are multiple weight estimations for a word,
    it averages the weight between the two.
    """
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


def _reduce_by_difficulty(pairs: list):
    """
    This function applies a difficulty filter. An association between words is
    considedred easier the closer it is to 1.
    """
    diff_terms = []
    for sys in pairs:
        trimmed = []
        for k, v in sys[1].items():
            if sys[1].get(k) >= args.difficulty:
                trimmed.append({k: v})
        if trimmed:
            diff_terms.append([sys[0], dict(ChainMap(*trimmed))])
    return diff_terms


def _reduce_per_sysnet(pairs: list):
    """
    This function applies a filter reducing the number of pairs for each Sysnet.
    """
    reduced_terms = []
    for sys in temp_pairs:
        reduced_terms.append(
            [sys[0], {k: sys[1][k] for k in list(sys[1])[: args.per_sysnet]}]
        )
    return reduced_terms


def _create_final_pairs_file(pairs: list, images_path: pathlib.Path):
    """
    This function writes to a .tsv file with the final version of the pairs to be
    used in the game.
    """
    cur_dir = os.getcwd()

    os.chdir(images_path)
    final_pairs = []
    for pair in pairs:
        for term in pair[1].items():
            image_path = (
                os.getcwd()
                + "/"
                + pair[0]
                + "/"
                + str(random.choice(os.listdir(pair[0])))
            )
            final_pairs.append(term[0] + "\t" + image_path + "\n")

    os.chdir(cur_dir)
    with open("image_data.tsv", "w", encoding="utf-8") as f:
        for p in final_pairs:
            f.write(p)
    print("Path to final pairs file: ", os.getcwd() + "/" + "image_data.tsv")


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
        temp_pairs = _reduce_by_difficulty(possible_pairs)
    else:
        temp_pairs = possible_pairs

    if args.per_sysnet:
        temp_pairs = _reduce_by_difficulty(temp_pairs)

    if args.num_sysnets:
        temp_pairs = [random.choice(temp_pairs) for _ in range(args.num_sysnets)]

    _create_final_pairs_file(temp_pairs, args.image_path)


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
