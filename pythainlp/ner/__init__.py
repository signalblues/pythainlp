# -*- coding: utf-8 -*-
"""
Named-entity recognizer
"""
from pythainlp.corpus import download, get_file, stopwords
from pythainlp.tag import pos_tag
from pythainlp.tokenize import word_tokenize
from pythainlp.util import is_thaiword

try:
    import sklearn_crfsuite
except ImportError:
    from pythainlp.tools import install_package

    install_package("sklearn-crfsuite")
    try:
        import sklearn_crfsuite
    except ImportError:
        raise ImportError("ImportError: Try 'pip install sklearn-crfsuite'")


_WORD_TOKENIZER = "newmm"  # ตัวตัดคำ
_STOPWORDS = stopwords.words("thai")


def _is_stopword(word):  # เช็คว่าเป็นคำฟุ่มเฟือย
    return word in _STOPWORDS


def _doc2features(doc, i):
    word = doc[i][0]
    postag = doc[i][1]

    # Features from current word
    features = {
        "word.word": word,
        "word.stopword": _is_stopword(word),
        "word.isthai": is_thaiword(word),
        "word.isspace": word.isspace(),
        "postag": postag,
        "word.isdigit()": word.isdigit(),
    }
    if word.isdigit() and len(word) == 5:
        features["word.islen5"] = True

    # Features from previous word
    if i > 0:
        prevword = doc[i - 1][0]
        prevpostag = doc[i - 1][1]
        prev_features = {
            "word.prevword": prevword,
            "word.previsspace": prevword.isspace(),
            "word.previsthai": is_thaiword(prevword),
            "word.prevstopword": _is_stopword(prevword),
            "word.prevpostag": prevpostag,
            "word.prevwordisdigit": prevword.isdigit(),
        }
        features.update(prev_features)
    else:
        features["BOS"] = True  # Special "Beginning of Sequence" tag

    # Features from next word
    if i < len(doc) - 1:
        nextword = doc[i + 1][0]
        nextpostag = doc[i + 1][1]
        next_features = {
            "word.nextword": nextword,
            "word.nextisspace": nextword.isspace(),
            "word.nextpostag": nextpostag,
            "word.nextisthai": is_thaiword(nextword),
            "word.nextstopword": _is_stopword(nextword),
            "word.nextwordisdigit": nextword.isdigit(),
        }
        features.update(next_features)
    else:
        features["EOS"] = True  # Special "End of Sequence" tag

    return features


class ThaiNameRecognizer:
    def __init__(self):
        """
        Thai named-entity recognizer
        """
        self.__data_path = get_file("thainer")
        if not self.__data_path:
            download("thainer")
            self.__data_path = get_file("thainer")
        self.crf = sklearn_crfsuite.CRF(
            algorithm="lbfgs",
            c1=0.1,
            c2=0.1,
            max_iterations=500,
            all_possible_transitions=True,
            model_filename=self.__data_path,
        )

    def get_ner(self, text, pos=True):
        """
        Get named-entities in text

        :param string text: Thai text
        :param boolean pos: get Part-Of-Speech tag (True) or get not (False)

        :return: list of strings with name labels (and part-of-speech tags)

        **Example**::
            >>> from pythainlp.ner import ThaiNameRecognizer
            >>> ner = ThaiNameRecognizer()
            >>> ner.get_ner("วันที่ 15 ก.ย. 61 ทดสอบระบบเวลา 14:49 น.")
            [('วันที่', 'JSBR', 'O'), (' ', 'NCMN', 'O'), ('15', 'NCNM', 'B-DATE'),
            (' ', 'NCMN', 'I-DATE'), ('ก.ย.', 'CMTR', 'I-DATE'), (' ', 'NCMN', 'I-DATE'),
            ('61', 'NCNM', 'I-DATE'), (' ', 'NCMN', 'O'), ('ทดสอบ', 'VACT', 'O'),
            ('ระบบ', 'NCMN', 'O'), ('เวลา', 'NCMN', 'O'), (' ', 'NCMN', 'O'),
            ('14', 'NCNM', 'B-TIME'), (':', 'PUNC', 'I-TIME'), ('49', 'NCNM', 'I-TIME'),
            (' ', 'NCMN', 'I-TIME'), ('น.', 'CMTR', 'I-TIME')]
            >>> ner.get_ner("วันที่ 15 ก.ย. 61 ทดสอบระบบเวลา 14:49 น.", pos=False)
            [('วันที่', 'O'), (' ', 'O'), ('15', 'B-DATE'), (' ', 'I-DATE'),
            ('ก.ย.', 'I-DATE'), (' ', 'I-DATE'), ('61', 'I-DATE'), (' ', 'O'),
            ('ทดสอบ', 'O'), ('ระบบ', 'O'), ('เวลา', 'O'), (' ', 'O'), ('14', 'B-TIME'),
            (':', 'I-TIME'), ('49', 'I-TIME'), (' ', 'I-TIME'), ('น.', 'I-TIME')]
        """
        self.__tokens = word_tokenize(text, engine=_WORD_TOKENIZER)
        self.__pos_tags = pos_tag(self.__tokens, engine="perceptron")
        self.__x_test = self.__extract_features(
            [(data, self.__pos_tags[i][1]) for i, data in enumerate(self.__tokens)]
        )
        self.__y = self.crf.predict_single(self.__x_test)

        if pos:
            return [
                (self.__tokens[i], self.__pos_tags[i][1], data)
                for i, data in enumerate(self.__y)
            ]

        return [(self.__tokens[i], data) for i, data in enumerate(self.__y)]

    def __extract_features(self, doc):
        return [_doc2features(doc, i) for i in range(len(doc))]

    def __get_labels(self, doc):
        return [tag for (token, postag, tag) in doc]

    def __get_model(self):
        return self.crf
