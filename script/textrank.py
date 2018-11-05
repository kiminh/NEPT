#! /usr/bin/python
'''Generate the textrank of words by using jieba-zh_TW package.
Repo of jieba-zh_TW: https://github.com/ldkrsi/jieba-zh_TW.git

eg:
    <source.data>                ->             <tags.json>
    eventId    title    otherCol                [{eventId: [word]},...]
    event1     title1   xxx                     event1: [word1, word2, word3 ....]
    event2     title2   xxx                     event2: [word1, word2, word3 ....]
    ...
'''
import argparse
import json
import pickle as pickle

from jieba import analyse
import jieba
from tqdm import tqdm
from gensim.models import Word2Vec

PARSER = argparse.ArgumentParser()
PARSER.add_argument("file",
                    type=str,
                    help="Relative path of file which is to be converted.")
PARSER.add_argument("-o",
                    "--output",
                    default='./data/textrank',
                    type=str,
                    help="Output the prefix of converted file.")
PARSER.add_argument("--textrank_word2vec",
                    type=bool,
                    default=False)
PARSER.add_argument("--textrank_idf",
                    type=bool,
                    default=False)
ARGS = PARSER.parse_args()
FILEPATH = ARGS.file
OUTPUT = ARGS.output

def word2vec_train(filepath: str):
    '''
    Return a Word2VecKeyedVectors
    '''
    print("Train word2vec from {}".format(filepath))
    with open(filepath, 'rt') as fin:
        textrank = analyse.TextRank()
        jieba.set_dictionary("./jieba-zh_TW/jieba/dict.txt")
        sentences = []
        for line in tqdm(fin):
            event_id, *event_description_list = line.strip().split(',')
            event_description = " ".join(event_description_list)
            sentence = []
            for word_pair in textrank.tokenizer.cut(event_description):
                if textrank.pairfilter(word_pair):
                    sentence.append(word_pair.word)
            sentences.append(sentence)
        model = Word2Vec(sentences, size=64,
                         alpha=0.025, window=2,
                         min_count=1, max_vocab_size=None,
                         sample=0.001, seed=1,
                         workers=3, min_alpha=0.0001,
                         sg=0, hs=0,
                         negative=5, ns_exponent=0.75,
                         cbow_mean=1,
                         iter=10, null_word=0,
                         trim_rule=None, sorted_vocab=1,
                         batch_words=10000, compute_loss=False,
                         callbacks=(), max_final_vocab=None)
        model.save(OUTPUT+'.model')
        return model.wv

def event_title_cut(filepath: str, word_vector=None, tfidf=None) -> dict:
    '''Return a dict{event_id: [words]} '''
    tag_dict = dict()
    jieba.set_dictionary("./jieba-zh_TW/jieba/dict.txt")
    with open(filepath, 'rt') as fin:
        for line in tqdm(fin):
            event_id, event_title, *event_description_list = line.strip().split(',')
            event_description = " ".join(event_description_list)
            title_tags = [(word, 1.0) for word in jieba.analyse.extract_tags(event_title)]
            if tfidf is not None:
                textrank_result = jieba.analyse.textrank_vsm(event_description, topK=10, withWeight=True, allowPOS=('ns', 'n'), vsm=tfidf)
            elif word_vector is not None:
                textrank_result = jieba.analyse.textrank_similarity(event_description, topK=10, withWeight=True, allowPOS=('ns', 'n'), word_embedding=word_vector),
            else:
                textrank_result = jieba.analyse.textrank(event_description, topK=10, withWeight=True, allowPOS=('ns', 'n')),
            tags = title_tags + textrank_result[0]
            tag_dict[int(event_id)] = tags
    return tag_dict
if __name__ == "__main__":
    IDF=None
    WORD2VEC=None
    if ARGS.textrank_idf:
        IDF = pickle.load(open("vsm_model.pickle", 'rb'))
    if ARGS.textrank_word2vec:
        WORD2VEC = word2vec_train(FILEPATH)
    EVENT_TITLE_TAG_DICT = event_title_cut(FILEPATH, tfidf=IDF, word_vector=WORD2VEC)
    with open(OUTPUT+".json", 'w', encoding='utf-8') as json_file:
        json.dump(EVENT_TITLE_TAG_DICT,
                  json_file,
                  ensure_ascii=False)
    with open(OUTPUT+".txt", 'w', encoding="utf-8") as fout:
        for key, value in EVENT_TITLE_TAG_DICT.items():
            fout.write("{}, {}\n".format(key, '/ '.join([x[0] for x in value])))
    with open(OUTPUT+"_mapping.txt", 'w') as fout:
        corpus = set([word[0] for word_list in EVENT_TITLE_TAG_DICT.values() for word in word_list])
        for index, word in enumerate(corpus):
            fout.write('w{},{}\n'.format(index, word))
