# models.py

import math
from utils import SentimentExample
from typing import List
from collections import Counter
import time
from tokenizers import Tokenizer
import numpy as np
from tqdm import tqdm

import gensim.downloader as api


class FeatureExtractor(object):
    """
    Feature extraction base type. Takes a text and returns an indexed list of features.
    """

    def extract_features(self, text: str) -> Counter:
        """
        Extract features from a text represented as a list of words.
        :param text: words in the example to featurize
        :return: A feature vector. We suggest using a Counter[int], which can encode a sparse feature vector (only
        a few indices have nonzero value) in essentially the same way as a map. However, you can use whatever data
        structure you prefer, since this does not interact with the framework code.
        """
        raise Exception("Don't call me, call my subclasses")


class CountFeatureExtractor(FeatureExtractor):
    """
    Extracts count features from text - your tokenizer returns token ids; you count their occurences.
    """

    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.tokenizer)

    def extract_features(self, text: str) -> Counter:
        """
        TODO: Extract count features from a text represented as a list of words.
        The feature vector should be a Counter mapping from token ids to their counts in the text.

        Example:
        Input `text`: ["hi", "hi", "world"]
        If `self.tokenizer.token_to_id`: {0: "hi", 1: "world", 2: "foo"}
        Output: Counter({0: 2, 1: 1})
        Depending on your implementation, you may also want to explicitly handle cases of unseen tokens:
        Output: Counter({0: 2, 1: 1, 2: 0})
        (In the above case, the token "foo" is not in the text, so its count is 0.)
        
        """
    

        tokenized_text = self.tokenizer.tokenize(text, False)
        token_ids = [self.tokenizer.token_to_id.get(token) for token in tokenized_text if token in self.tokenizer.token_to_id]

        counter = Counter(token_ids)
    
        return counter


class CustomFeatureExtractor(FeatureExtractor):
    """
    Custom feature extractor that extracts features from a text using a custom tokenizer.
    """
    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.tokenizer)

    def extract_features(self, text: str) -> Counter:
        """
        TODO: Implement your own custom feature extractor. The returned format should be the same as in CountFeatureExtractor,
        a Counter mapping from feature ids to their values.
        """

        tokenized_text = self.tokenizer.tokenize(text, False)
        token_ids = [self.tokenizer.token_to_id.get(token) for token in tokenized_text if token in self.tokenizer.token_to_id]

        total = len(token_ids)
        
        counter = Counter(token_ids)

        term_freq = dict()
        for key in counter:
            term_freq[key] = math.log(1 + counter[key])
               
        return counter

class MeanPoolingWordVectorFeatureExtractor(FeatureExtractor):
    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer
        print("Loading word2vec model...")
        self.word_to_vector_model = api.load("glove-twitter-25")
        print("Word2vec model loaded")

    def __len__(self):
        # the glove twitter word vectors are 25 dim
        return 25

    def get_word_vector(self, word) -> np.ndarray:
        """
        TODO: Get the word vector for a word from self.word_to_vector_model. If the word is not in the vocabulary, return None.
        
        Example:
        Input `word`: "hello"
        Output: numpy array of 25 dimensions
        Input `word`: "328hdnsr32ion"
        Output: None
        """
        
        try:
            return self.word_to_vector_model[word]
        except:
            return None
        

    def extract_features(self, text: List[str]) -> Counter:
        """
        TODO: Extract mean pooling word vector features from a text represented as a list of words.
        Detailed instructions:
        1. Tokenize the text into words using self.tokenizer.tokenize.
        2. For each word, get its word vector (using get_word_vector method).
        3. Average all of the word vectors to get the mean pooling vector.
        4. Convert the mean pooling vector to a Counter mapping from token ids to their counts.
        Note: this last step is important because the framework requires features to be a Counter mapping
        from token ids to their counts, normally you would not need to do this conversion.
        Remember to ignore words that do not have a word vector.
        """
    
        tokenized_text = self.tokenizer.tokenize(text, False)
        
        #print("Tokenized text", tokenized_text)
        word_vectors = [self.get_word_vector(token) for token in tokenized_text if self.get_word_vector(token) is not None]
        mean_pooling_vector = np.mean(word_vectors, axis=0)

        #print("Mean pooling vector:", mean_pooling_vector)
        #vector_dict = {i: val for i, val in enumerate(mean_pooling_vector)}
  
        counter = Counter({i: mean_pooling_vector[i] for i in range(len(mean_pooling_vector))})
        
        return counter
    


class SentimentClassifier(object):
    """
    Sentiment classifier base type
    """

    def predict(self, text: List[str]) -> int:
        """
        :param text: words (List[str]) in the text to classify
        :return: Either 0 for negative class or 1 for positive class
        """
        raise Exception("Don't call me, call my subclasses")


class TrivialSentimentClassifier(SentimentClassifier):
    """
    Sentiment classifier that always predicts the positive class.
    """

    def predict(self, text: List[str]) -> int:
        return 1


def sigmoid(x: float) -> float:
    """
    Numerically stable sigmoid function, avoids overflow.
    A utility function for the logistic regression classifier.
    """
    if x < 0:
        return np.exp(x) / (1 + np.exp(x))
    return 1 / (1 + np.exp(-x))


class LogisticRegressionClassifier(SentimentClassifier):
    """
    Logistic regression classifier, uses a featurizer to transform text into feature vectors and learns a binary classifier.
    """

    def __init__(self, featurizer: FeatureExtractor):
        """
        Initialize the logistic regression classifier.
        Weights and bias are initialized to 0, and stored as attributes of the class.
        The featurizer is also stored as an attribute of the class.
        The dtype of the weights and bias is np.float64, don't change this.
        """
        self.featurizer = featurizer
        # weights are a fixed size numpy array, where size is the number of features in the featurizer
        # init weights to 0, could do small random numbers but it's common practice to do 0
        self.weights = np.zeros(len(self.featurizer), dtype=np.float64)
        self.bias = 0

    def predict(self, text: str) -> int:
        """
        TODO: Predict the sentiment of a text, should be either 0 or 1.
        You will need to use the sigmoid function from above, which is already implemented.
        Detailed instructions:
        1. Extract features from the text using self.featurizer.extract_features.
        2. Compute the score as the (sum of the product of the weights and the features) plus the bias.
        3. Compute the sigmoid of the score.
        4. Return 1 if the sigmoid score is greater than or equal to 0.5, otherwise return 0.
        
        Example:
        Input `text`: "hi hi world"
        If `self.weights`: [1, 2, 10]
        If `self.bias`: 1
        If `self.featurizer.extract_features(text)`: Counter({0: 2, 1: 1, 2:0})
        Intermediate steps:
        score = 1*2 + 2*1 + 10*0 + 1 = 5
        sigmoid_score = sigmoid(5) = 0.993...
        Output: 1
        """

        features = self.featurizer.extract_features(text)

        score = self.bias

        for feature, count in features.items():
            if feature < len(self.weights):
                score += count * self.weights[feature]

        sigmoid_score = sigmoid(score)

        return 1 if sigmoid_score >= 0.5 else 0

    def set_weights(self, weights: np.ndarray):
        """
        Set the weights of the model.
        """
        self.weights = weights

    def set_bias(self, bias: float):
        """
        Set the bias of the model.
        """
        self.bias = bias

    def get_weights(self):
        return self.weights

    def get_bias(self):
        return self.bias

    def training_step(self, batch_exs: List[SentimentExample], learning_rate: float):
        """
        TODO: Update the weights and bias of the model from a batch of examples, using the learning rate.
        Detailed instructions:
        1. Iterate over the batch of examples.
            a. For each example, extract features and predict the label.
            b. Calculate the loss for the example.
        2. Update the weights and bias using the loss, using the learning rate and the batch size.
        
        Example:
        Input `batch_exs`: [SentimentExample(words="hi hi world", label=1), SentimentExample(words="foo bar", label=0)]
        Input `learning_rate`: 0.5
        If `self.weights`: [-2, 1, 2]
        If `self.bias`: -1
        If `self.featurizer.extract_features(batch_exs[0].words)`: Counter({0: 2, 1: 1})
        If `self.featurizer.extract_features(batch_exs[1].words)`: Counter({2: 1})
        Output:
        set `self.weights`: [-1.5, 1.25, 1.75]
        set `self.bias`: -0.25
        """
        total_weight_updates = np.zeros_like(self.weights)
        total_bias_update = 0.0
        batch_size = len(batch_exs)

        bias_update = 0.0  

        for example in batch_exs:
            y = example.label  # True label
            features = self.featurizer.extract_features(example.words)

            #print(type(features))
            #print(type(features[1]))
            #print(features[1])
           

            y_hat = self.predict(example.words)
  
            error = y - y_hat  # Gradient of loss function
            
         
            for feature, count in features.items():
               
                if feature < len(self.weights):
                    total_weight_updates[feature] += error * count  

          
            bias_update += error  

        self.weights += (learning_rate / batch_size) * total_weight_updates
        self.bias += (learning_rate / batch_size) * bias_update

    

        #Using cross-entropy loss as defined in book
        #L(y^, y) = -[ylogy^ + (1-y)log(1-y^)]

        #loss = -(y*math.log(y_hat) + (1-y)*math.log(1-y_hat))
   
        


def get_accuracy(predictions: List[int], labels: List[int]) -> float:
    """
    Calculate the accuracy of the predictions.
    """
    num_correct = 0
    num_total = len(predictions)
    for i in range(num_total):
        if predictions[i] == labels[i]:
            num_correct += 1
    return num_correct / num_total


def run_model_over_dataset(
    model: SentimentClassifier, dataset: List[SentimentExample]
) -> List[int]:
    """
    Run the model over a dataset and return the predictions.
    """
    predictions = []
    for ex in dataset:
        predictions.append(model.predict(ex.words))
    return predictions


def train_logistic_regression(
    train_exs: List[SentimentExample],
    dev_exs: List[SentimentExample],
    feat_extractor: FeatureExtractor,
    learning_rate: float = 0.01,
    batch_size: int = 10,
    epochs: int = 10,
) -> LogisticRegressionClassifier:
    """
    TODO: Train a logistic regression model.
    :param train_exs: training set, List of SentimentExample objects
    :param feat_extractor: feature extractor to use
    :return: trained LogisticRegressionClassifier model
    """

    ##########################################
    # Initialize the model and
    # any other variables you want to keep track of
    ##########################################

    model = LogisticRegressionClassifier(feat_extractor)

    for epoch in range(epochs):
        np.random.shuffle(train_exs)

        for i in range(0, len(train_exs), batch_size):
            batch_data = train_exs[i : i + batch_size]
            model.training_step(batch_data, learning_rate)

        #predictions = run_model_over_dataset(model, dev_exs)
        #accuracy = get_accuracy(predictions, [ex.label for ex in dev_exs])

    return model


    ##########################################
    # Learning rate scheduler
    # We don't ask you to implement this, but modifying the 
    # learning rate is a common technique to help with convergence.
    ##########################################
    # exponential decay learning rate scheduler
    scheduler = lambda epoch: learning_rate * (0.95**epoch)

    pbar = tqdm(range(epochs))
    for epoch in pbar:

        ##########################################
        # Shuffle the training examples
        # Instead of modifying the train_exs list,
        # just set shuffled_train_exs to a new list 
        # with the same elements but in a random order
        # This step helps prevent overfitting
        ##########################################
        shuffled_train_exs = []
        raise Exception("TODO: Implement this section")

        ##########################################
        # Iterate over batches of training examples
        ##########################################
        for i in range(0, len(shuffled_train_exs), batch_size):
            batch_exs = shuffled_train_exs[i : i + batch_size]

            ##########################################
            # Get the current learning rate from your scheduler
            ##########################################
            cur_learning_rate = scheduler(epoch)

            ##########################################
            # Update the weights and bias of the model using this batch of examples and the current learning rate
            # (hint: this is running a training step with a batch of examples)
            ##########################################
            raise Exception("TODO: Implement this section")

        ##########################################
        # Evaluate on the dev set
        # save the best model so far by dev accuracy
        # you may find the run_model_over_dataset 
        # and get_accuracy functions helpful
        ##########################################
        raise Exception("TODO: Implement this section")

        ##########################################
        # Log any metrics you want here, tqdm will
        # pass the metrics dictionary to the progress bar (pbar)
        # your metrics should probably include the best dev accuracy, current dev accuracy
        # and look something like this:
        # metrics = {"best_dev_acc": 0.9, "cur_dev_acc": 0.5}
        # this step is helpful for debugging and making sure you are saving the best model so far
        # at the end of training, your 'best_dev_acc' should be the best accuracy on the dev set
        ##########################################
        metrics = {}
        raise Exception("TODO: Implement this section")

        # if metrics is not empty, update the progress bar
        if len(metrics) > 0:
            pbar.set_postfix(metrics)

    ##########################################
    # Set the weights and bias of the model to
    # the best model so far by dev accuracy
    ##########################################
    raise Exception("TODO: Implement this section")

    return model


def train_model(
    args,
    train_exs: List[SentimentExample],
    dev_exs: List[SentimentExample],
    tokenizer: Tokenizer,
    learning_rate: float,
    batch_size: int,
    epochs: int,
) -> SentimentClassifier:
    """
    Main entry point for your modifications. Trains and returns one of several models depending on the args
    passed in from the main method. You may modify this function, but probably will not need to.
    :param args: args bundle from sentiment_classifier.py
    :param train_exs: training set, List of SentimentExample objects
    :param dev_exs: dev set, List of SentimentExample objects. You can use this for validation throughout the training
    process, but you should *not* directly train on this data.
    :return: trained SentimentClassifier model, of whichever type is specified
    """
    # Initialize feature extractor
    if args.feats == "COUNTER":
        feat_extractor = CountFeatureExtractor(tokenizer)
    elif args.feats == "WV":
        feat_extractor = MeanPoolingWordVectorFeatureExtractor(tokenizer)
    elif args.feats == "CUSTOM":
        feat_extractor = CustomFeatureExtractor(tokenizer)

    # Train the model
    if args.model == "TRIVIAL":
        model = TrivialSentimentClassifier()
    elif args.model == "LR":
        model = train_logistic_regression(
            train_exs,
            dev_exs,
            feat_extractor,
            learning_rate=learning_rate,
            batch_size=batch_size,
            epochs=epochs,
        )
    else:
        raise Exception("Pass in TRIVIAL or LR to run the appropriate system")
    return model
