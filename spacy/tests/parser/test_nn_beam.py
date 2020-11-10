# coding: utf8
from __future__ import unicode_literals

import pytest
import hypothesis
import hypothesis.strategies
import numpy
from spacy.vocab import Vocab
from spacy.language import Language
from spacy.pipeline import DependencyParser
from spacy.pipeline._parser_internals.arc_eager import ArcEager
from spacy.tokens import Doc
from spacy.pipeline._parser_internals._beam_utils import ParserBeam
from spacy.pipeline._parser_internals.stateclass import StateClass
from spacy.training import Example
from thinc.tests.strategies import ndarrays_of_shape


@pytest.fixture(scope="module")
def vocab():
    return Vocab()


@pytest.fixture(scope="module")
def moves(vocab):
    aeager = ArcEager(vocab.strings, {})
    aeager.add_action(0, "")
    aeager.add_action(1, "")
    aeager.add_action(2, "nsubj")
    aeager.add_action(2, "punct")
    aeager.add_action(2, "aux")
    aeager.add_action(2, "nsubjpass")
    aeager.add_action(3, "dobj")
    aeager.add_action(2, "aux")
    aeager.add_action(4, "ROOT")
    return aeager


@pytest.fixture(scope="module")
def docs(vocab):
    return [
        Doc(
            vocab,
            words=["Rats", "bite", "things"],
            heads=[1, 1, 1],
            deps=["nsubj", "ROOT", "dobj"],
            sent_starts=[True, False, False]
        )
    ]


@pytest.fixture(scope="module")
def examples(docs):
    return [Example(doc, doc.copy()) for doc in docs]


@pytest.fixture
def states(docs):
    return [StateClass(doc) for doc in docs]


@pytest.fixture
def tokvecs(docs, vector_size):
    output = []
    for doc in docs:
        vec = numpy.random.uniform(-0.1, 0.1, (len(doc), vector_size))
        output.append(numpy.asarray(vec))
    return output


@pytest.fixture(scope="module")
def batch_size(docs):
    return len(docs)


@pytest.fixture(scope="module")
def beam_width():
    return 4

@pytest.fixture(params=[0.0, 0.5, 1.0])
def beam_density(request):
    return request.param

@pytest.fixture
def vector_size():
    return 6


@pytest.fixture
def beam(moves, examples, beam_width):
    states, golds, _ = moves.init_gold_batch(examples)
    return ParserBeam(moves, states, golds, width=beam_width, density=0.0)


@pytest.fixture
def scores(moves, batch_size, beam_width):
    return [
        numpy.asarray(
            numpy.random.uniform(-0.1, 0.1, (beam_width, moves.n_moves)), dtype="f"
        )
        for _ in range(batch_size)
    ]


def test_create_beam(beam):
    pass


def test_beam_advance(beam, scores):
    scores = scores[:len(beam.beams)]
    beam.advance(scores)


def test_beam_advance_too_few_scores(beam, scores):
    scores = scores[:len(beam.beams)]
    with pytest.raises(IndexError):
        beam.advance(scores[:-1])


def test_beam_parse(examples, beam_width):
    nlp = Language()
    parser = nlp.add_pipe("beam_parser")
    parser.cfg["beam_width"] = beam_width
    parser.add_label("nsubj")
    parser.initialize(lambda: examples)
    doc = nlp.make_doc("Australia is a country")
    parser(doc)




@hypothesis.given(hyp=hypothesis.strategies.data())
def test_beam_density(moves, examples, beam_width, hyp):
    beam_density = float(hyp.draw(hypothesis.strategies.floats(0.0, 1.0, width=32)))
    states, golds, _ = moves.init_gold_batch(examples)
    beam = ParserBeam(moves, states, golds, width=beam_width, density=beam_density)
    scores = [
        hyp.draw(ndarrays_of_shape((len(b), moves.n_moves)))
        for b in beam
    ]
    beam.advance(scores)
    print("Draw")
    for b in beam:
        beam_probs = b.probs
        assert b.min_density == beam_density
        assert beam_probs[-1] >= beam_probs[0] * beam_density
