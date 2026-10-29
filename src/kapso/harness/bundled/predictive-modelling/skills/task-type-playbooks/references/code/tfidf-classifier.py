"""Code example of TF-IDF + Classifier (from the benchmark's graph; the task's own inputs where the original named a public dataset)."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression

tfidf_features = FeatureUnion([
  ('word', TfidfVectorizer(max_features=50000, ngram_range=(1,2), analyzer='word')),
  ('char', TfidfVectorizer(max_features=50000, ngram_range=(2,5), analyzer='char'))
])
clf = Pipeline([
    ('features', tfidf_features),
    ('lr', LogisticRegression())
])
clf.fit(X_train, y_train)
