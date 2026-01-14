from pynetbox.core.query import RequestError


class DummyNetBoxRecord(dict):
    """
    Create a dummy representation of a NetBox object
    """

    raise_conflict_on_delete = False

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value

    def __iter__(self):
        return iter(self.items())

    def update(self, data: dict):
        for k, v in data.items():
            self[k] = v

    def delete(self):
        from unittest.mock import Mock

        if self.raise_conflict_on_delete:
            req = Mock()
            req.status_code = 409
            req.url = "dummy-url"
            req.reason = "Conflict"
            req.text = "Conflict"
            req.request.body = None
            raise RequestError(req)
        return True
