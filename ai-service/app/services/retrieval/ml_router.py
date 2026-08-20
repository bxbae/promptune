from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


class MLRetrievalRouter:
    def __init__(self):
        self.model = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(2, 5),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
            (
                "svc",
                LinearSVC(
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ])

    def fit(self, queries, labels):
        self.model.fit(queries, labels)
        return self

    def predict(self, query):
        return str(self.model.predict([query])[0])
