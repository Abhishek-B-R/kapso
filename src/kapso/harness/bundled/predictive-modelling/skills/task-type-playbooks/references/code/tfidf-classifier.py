"""TF-IDF with a linear classifier: a shape from a hand-written knowledge graph of
past competitions, not a method.

Parameters, the task's: `X_train` (texts) and `y_train`. The vectorisers are fitted
on the training rows only: fitting them on training and test rows together is the
leakage scan's violation. `max_features` is sized to memory; validation and the
blend with a fine-tuned transformer are not shown.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

tfidf_features = FeatureUnion([
    ("word", TfidfVectorizer(max_features=50000, ngram_range=(1, 2), analyzer="word")),
    ("char", TfidfVectorizer(max_features=50000, ngram_range=(2, 5), analyzer="char")),
])
classifier = Pipeline([("features", tfidf_features), ("lr", LogisticRegression(max_iter=1000))])
classifier.fit(X_train, y_train)
