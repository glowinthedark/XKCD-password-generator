#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function

import argparse
import math
import os
import os.path
import random
import re
import sys

from io import open

__LICENSE__ = """
Copyright (c) 2011 - 2018, Steven Tobin and Contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# random.SystemRandom() should be cryptographically secure
try:
    rng = random.SystemRandom
except AttributeError as ex:
    sys.stderr.write("WARNING: System does not support cryptographically "
                     "secure random number generator or you are using Python "
                     "version < 2.4.\n")
    if "XKCDPASS_ALLOW_WEAKRNG" in os.environ or \
       "--allow-weak-rng" in sys.argv:
        sys.stderr.write("Continuing with less-secure generator.\n")
        rng = random.Random
    else:
        raise ex


# Python 3 compatibility
if sys.version_info[0] >= 3:
    raw_input = input
    xrange = range


DEFAULT_WORDFILE = "eff-long"
ALLOWED_SYMBOLS = '!#$%&()*+,-.:;<=>?@[]^_{|}~'


def validate_options(parser, options):
    """
    Given a parsed collection of options, performs various validation checks.
    """

    if options.max_length < options.min_length:
        sys.stderr.write("Warning: maximum word length less than minimum. "
                         "Setting maximum equal to minimum.\n")
        # sys.exit(1)

    wordfile = locate_wordfile(options.wordfile)
    if not wordfile:
        sys.stderr.write("Could not find a word file, or word file does "
                         "not exist.\n")
        sys.exit(1)


def locate_wordfile(wordfile=None):
    """
    Locate a wordfile from provided name/path. Return a path to wordfile
    either from static directory, the provided path or use a default.
    """
    common_word_files = []
    static_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static')

    if wordfile is not None:
        # wordfile can be in static dir or provided as a complete path
        common_word_files.append(os.path.join(static_dir, wordfile))
        common_word_files.append(os.path.expanduser(wordfile))

    common_word_files.extend([
        os.path.join(static_dir, DEFAULT_WORDFILE),
        "/usr/share/cracklib/cracklib-small",
        "/usr/share/dict/cracklib-small",
        "/usr/dict/words",
        "/usr/share/dict/words"])

    for wfile in common_word_files:
        if os.path.isfile(wfile):
            return wfile


def generate_wordlist(wordfile=None,
                      min_length=5,
                      max_length=9,
                      valid_chars='.'):
    """
    Generate a word list from either a kwarg wordfile, or a system default
    valid_chars is a regular expression match condition (default - all chars)
    """

    # deal with inconsistent min and max, erring toward security
    if min_length > max_length:
        max_length = min_length
    wordfile = locate_wordfile(wordfile)

    words = set()

    regexp = re.compile("^{0}{{{1},{2}}}$".format(valid_chars,
                                                  min_length,
                                                  max_length))
    # read words from file into wordlist
    with open(wordfile, encoding='utf-8') as wlf:
        for line in wlf:
            thisword = line.strip()
            if regexp.match(thisword) is not None:
                words.add(thisword)

    return list(words)  # deduplicate, just in case


def wordlist_to_worddict(wordlist):
    """
    Takes a wordlist and returns a dictionary keyed by the first letter of
    the words. Used for acrostic pass phrase generation
    """

    worddict = {}

    # Maybe should be a defaultdict, but this reduces dependencies
    for word in wordlist:
        try:
            worddict[word[0]].append(word)
        except KeyError:
            worddict[word[0]] = [word, ]

    return worddict


def verbose_reports(wordlist, options):
    """
    Report entropy metrics based on word list and requested password size"
    """

    if options.acrostic:
        worddict = wordlist_to_worddict(wordlist)
        numwords = len(options.acrostic)
        length = 0
        for char in options.acrostic:
            length += len(worddict.get(char, []))
    else:
        length = len(wordlist)
        numwords = options.numwords

    bits = math.log(length, 2)

    print("With the current options, your word list contains {0} words."
          .format(length))

    print("A {0} word password from this list will have roughly "
          "{1} ({2:.2f} * {3}) bits of entropy,"
          "".format(numwords, int(bits * numwords), bits, numwords))
    print("assuming truly random word selection.\n")


def find_acrostic(acrostic, worddict):
    """
    Constrain choice of words to those beginning with the letters of the
    given word (acrostic).
    Second argument is a dictionary (output of wordlist_to_worddict)
    """

    words = []

    for letter in acrostic:
        try:
            words.append(rng().choice(worddict[letter]))
        except KeyError:
            sys.stderr.write("No words found starting with " + letter + "\n")
            sys.exit(1)
    return words


def choose_words(wordlist, numwords):
    """
    Choose numwords randomly from wordlist
    """

    return [rng().choice(wordlist) for i in xrange(numwords)]


def try_input(prompt, validate):
    """
    Suppress stack trace on user cancel and validate input with supplied
    validate callable.
    """

    try:
        answer = raw_input(prompt)
    except (KeyboardInterrupt, EOFError):
        # user cancelled
        print("")
        sys.exit(0)

    # validate input
    return validate(answer)


def alternating_case(words):
    """
    Set EVERY OTHER word to UPPER case.
    """
    return [word.upper()
            if i % 2 == 0
            else word
            for i, word in enumerate(lower_case(words))]


def upper_case(words):
    """
    Set ALL words to UPPER case.
    """
    return [w.upper() for w in words]

def first_upper_case(words):
    """
    Set First character of each word to UPPER case.
    """
    return [w.capitalize() for w in words]

def sentence_case(words):
    """
    Set First character of first word to UPPER case.
    """
    return [w.capitalize() if i == 0 else w for i, w in enumerate(words)]

def lower_case(words):
    """
    Set ALL words to LOWER case.
    """
    return [w.lower() for w in words]

def capitalize_case(words):
    """
    Set first letter of each words to UPPER case aka Capitalize.
    """
    return [w.capitalize() for w in words]


def random_case(words, testing=False):
    """
    Set RANDOM words to UPPER case.
    """
    def make_upper(word):
        """Return 'word.upper()' on a random basis."""
        if testing:
            random.seed(word)

        if random.choice([True, False]):
            return word.upper()
        else:
            return word

    return [make_upper(word) for word in lower_case(words)]


CASE_METHODS = {"sentence": sentence_case,
                "alternating": alternating_case,
                "upper": upper_case,
                "lower": lower_case,
                "random": random_case,
                "first": first_upper_case,
                "capitalize":capitalize_case}



def set_case(words, method="lower", testing=False):
    """
    Perform capitalization on some or all of the strings in `words`.

    Default method is "lower".

    Args:
        words (list):   word list generated by `choose_words()` or
                        `find_acrostic()`.
        method (str):   one of {"alternating", "upper", "lower",
                        "random"}.
        testing (bool): only affects method="random".
                        If True: the random seed will be set to each word
                        prior to choosing True or False before setting the
                        case to upper. This way we can test that random is
                        working by giving different word lists.
    """
    if (method == "random") and (testing):
        return random_case(words, testing=True)
    else:
        return CASE_METHODS[method](words)


def generate_xkcdpassword(wordlist,
                          numwords=6,
                          interactive=False,
                          acrostic=False,
                          delimiter=".",
                          case="sentence",
                          num_digits=1,
                          num_symbols=1):
    """
    Generate an XKCD-style password from the words in wordlist.
    """

    passwd = None

    # generate the worddict if we are looking for acrostics
    if acrostic:
        worddict = wordlist_to_worddict(wordlist)

    def gen_passwd():
        if not acrostic:
            words = choose_words(wordlist, numwords)
        else:
            words = find_acrostic(acrostic, worddict)

        pw = delimiter.join(set_case(words, method=case))

        digits = ''

        if num_digits:
            for i in range(num_digits):
                digits += str(random.randint(0, 9))

        symbols = ''

        if num_symbols:
            for i in range(num_symbols):
                symbols += ALLOWED_SYMBOLS[random.randint(0, len(ALLOWED_SYMBOLS) - 1)]

        return pw + digits + symbols

    # useful if driving the logic from other code
    if not interactive:
        return gen_passwd()
        
    # else, interactive session
    else:
        # define input validators
        def accepted_validator(answer):
            return answer.lower().strip() in ["y", "yes"]

        # generate passwords until the user accepts
        accepted = False
        
        while not accepted:
            passwd = gen_passwd()
            print("Generated: " + passwd)
            accepted = try_input("Accept? [yN] ", accepted_validator)
            print('accepted', accepted)

        return passwd
        

def initialize_interactive_run(options):
    def n_words_validator(answer):
            """
            Validate custom number of words input
            """
            
            if isinstance(answer, str) and len(answer) == 0:
                return options.numwords
            try:
                number = int(answer)
                if number < 1:
                    raise ValueError
                return number
            except ValueError:
                sys.stderr.write("Please enter a positive integer\n")
                sys.exit(1)

    if not options.acrostic:
        n_words_prompt = ("Enter number of words (default {0}):\n".format(options.numwords))
        options.numwords = try_input(n_words_prompt, n_words_validator)
    else:
        options.numwords = len(options.acrostic)


def emit_passwords(wordlist, options):
    """ Generate the specified number of passwords and output them. """
    count = options.count
    while count > 0:
        print(
            generate_xkcdpassword(
                wordlist,
                interactive=options.interactive,
                numwords=options.numwords,
                acrostic=options.acrostic,
                delimiter=options.delimiter,
                case=options.case,
                num_digits=options.num_digits,
                num_symbols=options.num_symbols,

            ),
            end=options.separator)
        count -= 1


class XkcdPassArgumentParser(argparse.ArgumentParser):
    """ Command-line argument parser for this program. """

    def __init__(self, *args, **kwargs):
        super(XkcdPassArgumentParser, self).__init__(*args, **kwargs)

        self._add_arguments()

    def _add_arguments(self):
        """ Add the arguments needed for this program. """
        exclusive_group = self.add_mutually_exclusive_group()
        self.add_argument(
            "-w", "--wordfile",
            dest="wordfile", default=None, metavar="WORDFILE",
             help=(
                "Specify that the file WORDFILE contains the list"
                " of valid words from which to generate passphrases."
                " Provided wordfiles: eff-long (default), eff-short,"
                " eff-special, legacy, spa-mich (Spanish), fin-kotus (Finnish),"
                " fr-freelang (French), fr-corrected.txt (French), pt-ipublicis (Portuguese),"
                " ita-wiki (Italian), ger-anlx (German), eff_large_de.wordlist (German), nor-nb (Norwegian)"))
        self.add_argument(
            "--min",
            dest="min_length", type=int, default=3, metavar="MIN_LENGTH",
            help="Generate passphrases containing at least MIN_LENGTH words.")
        self.add_argument(
            "--max",
            dest="max_length", type=int, default=9, metavar="MAX_LENGTH",
            help="Generate passphrases containing at most MAX_LENGTH words.")
        exclusive_group.add_argument(
            "-n", "--numwords",
            dest="numwords", type=int, default=3, metavar="NUM_WORDS",
            help="Generate passphrases containing exactly NUM_WORDS words.")
        exclusive_group.add_argument(
            "-a", "--acrostic",
            dest="acrostic", default=False,
            help="Generate passphrases with an acrostic matching ACROSTIC.")
        self.add_argument(
            "-i", "--interactive",
            action="store_true", dest="interactive", default=False,
            help=(
                "Generate and output a passphrase, query the user to"
                " accept it, and loop until one is accepted."))
        self.add_argument(
            "-v", "--valid-chars",
            dest="valid_chars", default=".", metavar="VALID_CHARS",
            help=(
                "Limit passphrases to only include words matching the regex"
                " pattern VALID_CHARS (e.g. '[a-z]')."))
        self.add_argument(
            "-V", "--verbose",
            action="store_true", dest="verbose", default=False,
            help="Report various metrics for given options.")
        self.add_argument(
            "-c", "--count",
            dest="count", type=int, default=5, metavar="COUNT",
            help="Generate COUNT passphrases.")
        self.add_argument(
            "-d", "--delimiter",
            dest="delimiter", default=".", metavar="DELIM",
            help="Separate words within a passphrase with DELIM.")
        self.add_argument(
            "-s", "--separator",
            dest="separator", default="\n", metavar="SEP",
            help="Separate generated passphrases with SEP.")
        self.add_argument(
            "-C", "--case",
            dest="case", type=str, metavar="CASE",
            choices=list(CASE_METHODS.keys()), default="sentence",
            help=(
                "Choose the method for setting the case of each word "
                "in the passphrase. "
                "Choices: {cap_meths} (default: 'lower').".format(
                    cap_meths=list(CASE_METHODS.keys())
                )))
        self.add_argument(
            "--allow-weak-rng",
            action="store_true", dest="allow_weak_rng", default=False,
            help=(
                "Allow fallback to weak RNG if the "
                "system does not support cryptographically secure RNG. "
                "Only use this if you know what you are doing."))
        self.add_argument(
            "--num-symbols",
            dest="num_symbols", type=int, default=1, metavar="NUM_SYMBOLS",
            help=("Number of symbols to append"))
        self.add_argument(
            "--num-digits",
            dest="num_digits", type=int, default=1, metavar="NUM_DIGITS",
            help=("Number of digits to append"))


def main(argv=None):
    """ Mainline code for this program. """

    if argv is None:
        argv = sys.argv

    exit_status = 0

    try:
        program_name = os.path.basename(argv[0])
        parser = XkcdPassArgumentParser(prog=program_name)

        options = parser.parse_args(argv[1:])
        validate_options(parser, options)

        my_wordlist = generate_wordlist(
            wordfile=options.wordfile,
            min_length=options.min_length,
            max_length=options.max_length,
            valid_chars=options.valid_chars)

        if options.interactive:
            initialize_interactive_run(options)
        
        if options.verbose:
            verbose_reports(my_wordlist, options)

        emit_passwords(my_wordlist, options)

    except SystemExit as exc:
        exit_status = exc.code

    return exit_status


if __name__ == '__main__':
    exit_status = main(sys.argv)
    sys.exit(exit_status)
