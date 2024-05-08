from textual.validation import ValidationResult, Validator


class ValidFilePath(Validator):

    def validate(self, value: str) -> ValidationResult:
        if value.startswith("/") or value.endswith("/"):
            return self.failure("Path cannot start or end with a /")
        else:
            return self.success()


class ValidDirPath(Validator):

    def validate(self, value: str) -> ValidationResult:
        if value.startswith("/"):
            return self.failure("Path cannot start with a /")
        else:
            return self.success()


class ValidURL(Validator):
    def validate(self, value: str) -> ValidationResult:
        if "/" in value:
            return self.failure("URL cannot contain a /")
        else:
            return self.success()
