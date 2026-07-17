import tiktoken


class TokenCounter:
    def __init__(self, model: str) -> None:
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("o200k_base")

    def count(self, text: str) -> int:
        return len(self.encoding.encode(text))